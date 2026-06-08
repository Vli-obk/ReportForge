import asyncio
import csv
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, TypedDict

import pandas as pd
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# ~12 000 characters ≈ 3 000 tokens; safe for gemini-2.0-flash (1M token window but we keep
# chunks small so structured-extraction prompts stay coherent and output fits max_tokens).
_CHUNK_SIZE = 12_000
_CHUNK_OVERLAP = 400

# ---------------------------------------------------------------------------
# Key pool — round-robin across all configured Gemini API keys.
# A key that returns 429 is cooled down for 60 s before being reused.
# ---------------------------------------------------------------------------

class _KeyPool:
    _COOLDOWN = 60  # seconds before a rate-limited key is retried

    def __init__(self, keys: List[str]):
        self._keys = list(keys)
        self._idx = 0
        self._cooldown_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def next(self) -> str:
        """Return the next available key (round-robin, skipping cooled-down ones)."""
        with self._lock:
            now = time.time()
            for _ in range(len(self._keys)):
                key = self._keys[self._idx % len(self._keys)]
                self._idx += 1
                if now >= self._cooldown_until.get(key, 0):
                    return key
            # All keys are rate-limited — return the one whose cooldown expires soonest
            key = min(self._keys, key=lambda k: self._cooldown_until.get(k, 0))
            logger.warning("gemini_all_keys_rate_limited")
            return key

    def mark_rate_limited(self, key: str) -> None:
        with self._lock:
            self._cooldown_until[key] = time.time() + self._COOLDOWN
            logger.warning("gemini_key_rate_limited", extra={"key_suffix": key[-6:], "cooldown_s": self._COOLDOWN})

    def __len__(self) -> int:
        return len(self._keys)


# Initialised lazily so tests can override settings before first use.
_key_pool: Optional[_KeyPool] = None
_pool_lock = threading.Lock()

def _get_key_pool() -> _KeyPool:
    global _key_pool
    if _key_pool is None:
        with _pool_lock:
            if _key_pool is None:
                keys = settings.gemini_key_pool
                _key_pool = _KeyPool(keys)
                logger.info("gemini_key_pool_initialized", extra={"key_count": len(keys)})
    return _key_pool


class GeminiError(Exception):
    pass


class GeminiUnavailableError(GeminiError):
    pass


class GeminiRateLimitError(GeminiError):
    pass


class ModelNotFoundError(GeminiError):
    pass


class GeminiTimeoutError(GeminiError):
    pass


class GeminiHealth(TypedDict):
    available: bool
    model_available: bool
    model: str
    error: Optional[str]


class GeminiService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 180,
        retries: int = 2,
        retry_delay: int = 10,
    ):
        self.base_url = (base_url or settings.GEMINI_API_URL).rstrip("/")
        self.model = model or settings.GEMINI_MODEL
        self.fallback_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        # api_key kwarg pins a specific key (used in tests); otherwise use the pool.
        self._pinned_key: Optional[str] = api_key
        self.api_version = settings.GEMINI_API_VERSION
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

    @property
    def api_key(self) -> str:
        return self._pinned_key or _get_key_pool().next()

    # ------------------------------------------------------------------ #
    # HTTP helpers                                                         #
    # ------------------------------------------------------------------ #

    def _headers(self, key: Optional[str] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        k = key or self.api_key
        if k and k.startswith(("ya29.", "ya29a", "ya29c", "ya29i")):
            headers["Authorization"] = f"Bearer {k}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        # One key per request — strict round-robin, no fallback within a call.
        current_key = self._pinned_key or _get_key_pool().next()

        params = dict(kwargs.pop("params", {}) or {})
        if current_key and "googleapis.com" in self.base_url:
            if not current_key.startswith(("ya29.", "ya29a", "ya29c", "ya29i")):
                params["key"] = current_key
        req_kwargs = {**kwargs, "headers": self._headers(current_key)}
        if params:
            req_kwargs["params"] = params

        try:
            return requests.request(method, f"{self.base_url}{path}", **req_kwargs)
        except requests.exceptions.Timeout as exc:
            raise GeminiTimeoutError("Gemini request timeout") from exc
        except requests.exceptions.ConnectionError as exc:
            raise GeminiUnavailableError("Gemini service unavailable") from exc

    async def _async_request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return await asyncio.to_thread(self._request, method, path, **kwargs)

    def _model_path(self, suffix: str = "") -> str:
        return f"/{self.api_version}/models/{self.model}{suffix}"

    # ------------------------------------------------------------------ #
    # Health / connectivity                                                #
    # ------------------------------------------------------------------ #

    def check_connection(self) -> bool:
        response = self._request("GET", self._model_path(), timeout=5)
        if response.status_code == 404:
            for fallback_model in self.fallback_models:
                if fallback_model == self.model:
                    continue
                current_model = self.model
                self.model = fallback_model
                fallback_response = self._request("GET", self._model_path(), timeout=5)
                if fallback_response.status_code != 404:
                    response = fallback_response
                    break
                self.model = current_model
            else:
                raise ModelNotFoundError(f"Model not installed: {self.model}")
        if response.status_code == 404:
            raise ModelNotFoundError(f"Model not installed: {self.model}")
        if response.status_code != 200:
            raise GeminiUnavailableError(f"Invalid Gemini response: {response.status_code}")
        try:
            response.json()
        except ValueError as exc:
            raise GeminiUnavailableError("Invalid response from Gemini") from exc
        return True

    def health_check(self) -> GeminiHealth:
        try:
            self.check_connection()
            return {"available": True, "model_available": True, "model": self.model, "error": None}
        except ModelNotFoundError as exc:
            return {"available": True, "model_available": False, "model": self.model, "error": str(exc)}
        except GeminiError as exc:
            return {"available": False, "model_available": False, "model": self.model, "error": str(exc)}

    async def async_health_check(self) -> GeminiHealth:
        return await asyncio.to_thread(self.health_check)

    def is_service_available(self) -> bool:
        try:
            return self.check_connection()
        except GeminiError as exc:
            logger.warning("gemini_connection_failed", extra={"model": self.model, "error": str(exc)})
            return False

    # ------------------------------------------------------------------ #
    # Generation                                                           #
    # ------------------------------------------------------------------ #

    def generate_sync(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str:
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")

        started = time.perf_counter()
        payload_json = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }

        # _request already rotates keys on 429; we just handle 404/5xx here.
        transient_retried = False
        for attempt in range(self.retries + 1):
            response = self._request("POST", self._model_path(":generateContent"), json=payload_json)

            if response.status_code == 429:
                # All keys exhausted by _request rotation
                raise GeminiRateLimitError("Gemini rate limit exceeded on all keys.")

            if response.status_code == 404:
                raise ModelNotFoundError(f"Model not installed: {self.model}")

            if response.status_code in (503, 502) and not transient_retried:
                transient_retried = True
                time.sleep(2)
                continue

            if response.status_code != 200:
                raise GeminiUnavailableError(f"Gemini API error: {response.status_code}")
            break

        elapsed = round(time.perf_counter() - started, 3)
        try:
            payload = response.json()  # type: ignore[union-attr]
        except ValueError as exc:
            raise GeminiUnavailableError("Invalid response from Gemini") from exc

        text = self._extract_response_text(payload)
        if text:
            logger.info("gemini_request_complete", extra={"model": self.model, "processing_time": elapsed})
            return text

        raise GeminiUnavailableError("Empty or unparseable response from Gemini")

    async def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str:
        return await asyncio.to_thread(self.generate_sync, prompt, temperature, max_tokens)

    # ------------------------------------------------------------------ #
    # Chunked extraction                                                   #
    # ------------------------------------------------------------------ #

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = _CHUNK_SIZE,
        overlap: int = _CHUNK_OVERLAP,
    ) -> List[str]:
        """Split text into overlapping chunks, breaking at paragraph/sentence boundaries."""
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                boundary = text.rfind("\n\n", start, end)
                if boundary != -1 and boundary > start + chunk_size // 2:
                    end = boundary + 2
                else:
                    boundary = text.rfind(". ", start, end)
                    if boundary != -1 and boundary > start + chunk_size // 2:
                        end = boundary + 2
            chunks.append(text[start:end])
            start = end - overlap
            if start >= len(text):
                break

        return chunks

    # Hard cap: insights extraction never needs more than ~15 000 tokens of input.
    # Larger inputs get truncated at a paragraph boundary to keep memory bounded.
    _EXTRACT_MAX_CHARS = 50_000

    async def extract_from_text(
        self, text: str, temperature: float = 0.3, max_tokens: int = 2000
    ) -> str:
        text = text.strip()
        if not text:
            raise ValueError("text cannot be empty")

        if len(text) > self._EXTRACT_MAX_CHARS:
            # Truncate at a paragraph boundary near the cap
            boundary = text.rfind("\n\n", 0, self._EXTRACT_MAX_CHARS)
            text = text[: boundary if boundary > self._EXTRACT_MAX_CHARS // 2 else self._EXTRACT_MAX_CHARS]
            logger.info("extract_text_truncated", extra={"original_chars": len(text), "capped_at": self._EXTRACT_MAX_CHARS})

        chunks = self._chunk_text(text)

        if len(chunks) == 1:
            return await self.generate(
                f"Extract concise insights from this PDF content:\n\n{text}",
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Process chunks sequentially to respect rate limits
        logger.info(
            "gemini_chunked_extraction",
            extra={"total_chunks": len(chunks), "text_length": len(text)},
        )
        part_results: List[str] = []
        for i, chunk in enumerate(chunks, 1):
            part_result = await self.generate(
                f"Extract key insights from this PDF excerpt (part {i} of {len(chunks)}):\n\n{chunk}",
                temperature=temperature,
                max_tokens=max(400, max_tokens // len(chunks)),
            )
            part_results.append(part_result)

        combined = "\n\n".join(f"[Part {i + 1}]\n{r}" for i, r in enumerate(part_results))
        return await self.generate(
            f"Synthesize these partial analyses of a multi-section PDF into one unified summary:\n\n{combined}",
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------ #
    # Structured extraction                                                #
    # ------------------------------------------------------------------ #

    def extract_structured_data(
        self, text: str, max_tokens: int = 8192, temperature: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Extract structured tabular data. Raises GeminiError subclasses on failure."""
        prompt = self._build_extraction_prompt(text)
        raw = self._generate_json_sync(prompt, temperature, max_tokens)
        return self._parse_json_response(raw)

    def _generate_json_sync(self, prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        """Like generate_sync but requests JSON output via responseMimeType.

        Sets thinkingBudget=0 because structured extraction is deterministic — no
        reasoning needed — and thinking tokens would eat into maxOutputTokens budget.
        """
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")

        started = time.perf_counter()
        payload_json = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        # _request rotates keys on 429; we just handle 404/5xx here.
        transient_retried = False
        for attempt in range(self.retries + 1):
            response = self._request("POST", self._model_path(":generateContent"), json=payload_json)

            if response.status_code == 429:
                raise GeminiRateLimitError("Gemini rate limit exceeded on all keys.")

            if response.status_code == 404:
                raise ModelNotFoundError(f"Model not installed: {self.model}")

            if response.status_code in (503, 502) and not transient_retried:
                transient_retried = True
                time.sleep(2)
                continue

            if response.status_code != 200:
                raise GeminiUnavailableError(f"Gemini API error: {response.status_code}")
            break

        elapsed = round(time.perf_counter() - started, 3)
        try:
            payload = response.json()  # type: ignore[union-attr]
        except ValueError as exc:
            raise GeminiUnavailableError("Invalid response from Gemini") from exc

        text_out = self._extract_response_text(payload)
        if text_out:
            logger.info("gemini_request_complete", extra={"model": self.model, "processing_time": elapsed})
            return text_out

        raise GeminiUnavailableError("Empty response from Gemini")

    def _build_extraction_prompt(self, text: str) -> str:
        return f"""You are a data extraction assistant. Extract structured data from the text below.

RULES:
- Return a JSON array of objects. Each object is one data record.
- If the text has tables, extract every row as an object with column names as keys.
- If the text has no tables but has statistics/figures, extract key-value pairs (e.g. {{"metric": "Unemployment rate", "value": 3.9, "period": "May 2025"}}).
- If no structured data at all exists, return an empty array: []
- Never return explanatory text — only the JSON array.
- Strip whitespace from all string values.
- Use numbers (not strings) for numeric values.

TEXT:
{text}"""

    # ------------------------------------------------------------------ #
    # Pipeline helpers                                                     #
    # ------------------------------------------------------------------ #

    def process_pdf_text_to_exports(
        self, text: str, csv_path: str, json_path: str
    ) -> List[Dict[str, Any]]:
        if not text.strip():
            logger.warning("gemini_empty_text")
            return []

        try:
            structured_data = self.extract_structured_data(text)
        except GeminiRateLimitError:
            logger.warning("gemini_rate_limited_export")
            return []
        except GeminiTimeoutError:
            logger.warning("gemini_timeout_export")
            return []
        except GeminiError as exc:
            logger.warning("gemini_extraction_error", extra={"error": str(exc)})
            return []

        logger.info("gemini_extracted_rows", extra={"rows": len(structured_data)})

        if structured_data:
            self.save_to_csv(structured_data, csv_path)
            self.save_to_json(structured_data, json_path)
            logger.info("gemini_exports_saved", extra={"csv": csv_path, "json": json_path})

        return structured_data

    def process_pdf_text_to_csv(self, text: str, output_path: str) -> List[Dict[str, Any]]:
        return self.process_pdf_text_to_exports(
            text,
            output_path,
            f"{os.path.splitext(output_path)[0]}.json",
        )

    def save_to_csv(self, structured_data: List[Dict[str, Any]], output_path: str) -> str:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            self.convert_to_dataframe(structured_data).to_csv(
                output_path, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8"
            )
            return output_path
        except Exception as exc:
            raise RuntimeError(f"Failed to save CSV: {exc}") from exc

    def save_to_json(self, structured_data: List[Dict[str, Any]], output_path: str) -> str:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump(structured_data, handle, ensure_ascii=False, indent=2)
            return output_path
        except Exception as exc:
            raise RuntimeError(f"Failed to save JSON: {exc}") from exc

    def convert_to_dataframe(self, structured_data: List[Dict[str, Any]]) -> pd.DataFrame:
        if not structured_data:
            return pd.DataFrame()
        return pd.DataFrame(structured_data)

    # ------------------------------------------------------------------ #
    # Response parsing                                                     #
    # ------------------------------------------------------------------ #

    def _extract_response_text(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        candidates = payload.get("candidates", [])
        if isinstance(candidates, list) and candidates:
            candidate = candidates[0]
            content = candidate.get("content")
            if isinstance(content, dict):
                parts = content.get("parts", [])
                if isinstance(parts, list):
                    text = "".join(
                        part.get("text", "") for part in parts if isinstance(part, dict)
                    )
                    if text.strip():
                        return text.strip()
            for key in ("output", "content", "text"):
                value = candidate.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for key in ("output", "response", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _parse_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        response_text = self._strip_code_fence(response_text.strip())
        try:
            data = json.loads(self._repair_json(response_text))
            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        data = value
                        break
                else:
                    return [self._validate_record(data)]
            if isinstance(data, list):
                return [self._validate_record(item) for item in data if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass

        try:
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                data = json.loads(self._repair_json(json_match.group(0)))
                if isinstance(data, list):
                    return [self._validate_record(item) for item in data if isinstance(item, dict)]
            logger.warning("gemini_json_parse_empty")
            return []
        except json.JSONDecodeError as exc:
            logger.warning("gemini_json_parse_failed", extra={"error": str(exc)})
            return []

    def _strip_code_fence(self, text: str) -> str:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        return text

    def _repair_json(self, text: str) -> str:
        # Remove trailing commas before } or ]
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        # If the array/object looks truncated, try to close it
        text = text.rstrip()
        if text and text[0] == '[' and not text.endswith(']'):
            # Strip trailing incomplete object/value
            last_complete = max(text.rfind('}'), text.rfind('"'))
            if last_complete > 0 and text[last_complete] == '}':
                text = text[:last_complete + 1] + ']'
            elif last_complete > 0:
                # Cut back to last complete object boundary
                cut = text.rfind('},')
                if cut > 0:
                    text = text[:cut + 1] + ']'
        return text

    def _validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {str(key).strip(): self._normalize_value(value) for key, value in record.items()}

    def _normalize_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (int, float, bool)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            parsed = self._parse_number(text)
            if parsed is not None:
                return parsed
            return text
        return value

    def _parse_number(self, value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            multiplier = 1
            if text.lower().endswith("k"):
                multiplier = 1000
                text = text[:-1]
            elif text.lower().endswith("m"):
                multiplier = 1_000_000
                text = text[:-1]
            try:
                if re.fullmatch(r"\(.+\)", text):
                    text = "-" + text[1:-1]
                return float(re.sub(r"[$,%\s,]", "", text)) * multiplier
            except ValueError:
                return None
        return None
