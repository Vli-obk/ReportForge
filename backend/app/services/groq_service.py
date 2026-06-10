import csv
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.3-70b-versatile"

_EXTRACTION_PROMPT = """You are a precise data extraction engine. Extract the main structured data from this document and return a JSON array.

RULES:
1. Find the dominant table or repeating structure. Use its REAL column headers as JSON keys (snake_case, max 40 chars).
2. Do NOT invent generic schemas like metric/value/unit — preserve the actual structure of the data.
   WRONG: [{{"metric":"Revenue","value":"1245300","unit":"USD","period":"2022"}}]
   RIGHT:  [{{"year":"2022","revenue":"1245300","net_income":"187600","margin":"15.1%"}}]
3. ALL rows MUST have the EXACT SAME keys. Fill missing cells with null.
4. ONLY exception: if the document is a compliance checklist or boolean matrix (OUI/NON/✓/✗ across many columns),
   use long format: [{{"entity":"...","field":"...","status":"OUI"}}]
5. Return ONLY the raw JSON array — no markdown, no explanation, nothing outside the brackets.

Document:
{text}

JSON array:"""

_TABLE_PROMPT = """You are a data extraction engine. Convert the PDF table(s) below into a JSON array.

RULES:
1. Use the FIRST ROW as column headers. Convert header text to snake_case (e.g. "Net Income" → "net_income").
2. Each subsequent row = one JSON object. Keep the WIDE format — do NOT melt or pivot the table.
   WRONG (melted): [{{"metric":"Revenue","value":"1245300","year":"2022"}}]
   RIGHT  (wide):  [{{"year":"2022","revenue":"1245300","net_income":"187600","eps":"2.34"}}]
3. ALL rows MUST have the EXACT SAME keys. Fill missing cells with null.
4. ONLY exception: if columns contain nothing but OUI/NON/YES/NO/✓/✗/x (boolean matrix / checklist),
   then DO convert to long format: [{{"entity":"...","field":"...","status":"OUI"}}]
5. Return ONLY the raw JSON array — no markdown, no explanation, no text outside the array.

Table(s) (page {page}):
{table_text}

JSON array:"""


class GroqError(Exception):
    pass


class GroqRateLimitError(GroqError):
    pass


class GroqUnavailableError(GroqError):
    pass


class GroqService:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate_sync(self, prompt: str, temperature: float = 0.3, max_tokens: int = 512) -> str:
        payload = {
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(_GROQ_URL, headers=self._headers(), json=payload, timeout=self.timeout)
            if resp.status_code == 429:
                raise GroqRateLimitError("Groq rate limit hit")
            if resp.status_code >= 500:
                raise GroqUnavailableError(f"Groq server error {resp.status_code}")
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (GroqRateLimitError, GroqUnavailableError):
            raise
        except requests.exceptions.Timeout:
            raise GroqUnavailableError("Groq request timed out")
        except Exception as exc:
            raise GroqUnavailableError(f"Groq request failed: {exc}") from exc

    def extract_structured_data(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured rows from document text. Returns list of dicts."""
        chunk = text[:8_000]
        prompt = _EXTRACTION_PROMPT.format(text=chunk)
        raw = self.generate_sync(prompt, temperature=0.1, max_tokens=2000)

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw.strip())

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try to salvage a partial JSON array (truncated response)
            bracket = raw.find("[")
            if bracket != -1:
                raw = raw[bracket:]
                # Close any open array
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    last_brace = raw.rfind("},")
                    if last_brace != -1:
                        try:
                            parsed = json.loads(raw[:last_brace + 1] + "]")
                        except json.JSONDecodeError:
                            logger.warning("groq_json_parse_failed", extra={"raw_preview": raw[:200]})
                            return []
                    else:
                        logger.warning("groq_json_parse_failed", extra={"raw_preview": raw[:200]})
                        return []
            else:
                logger.warning("groq_json_parse_failed", extra={"raw_preview": raw[:200]})
                return []

        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return []

        rows = [r for r in parsed if isinstance(r, dict) and r]
        if not rows:
            return []

        return self._normalize_columns(rows)

    def _normalize_columns(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize rows: uniform columns, drop sparse/empty cols, melt boolean matrix cols."""
        _empty = {None, "", "null", "none", "n/a", "na", "-", "—"}
        _bool_vals = {"oui", "non", "yes", "no", "true", "false", "1", "0", "x", "✓", "✗"}

        def _is_empty(v: Any) -> bool:
            return v is None or str(v).strip().lower() in _empty

        # Union of all keys (preserve insertion order)
        all_keys: list = []
        seen: set = set()
        for row in rows:
            for k in row.keys():
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)

        # Fill missing keys with None
        filled_rows = [{k: row.get(k, None) for k in all_keys} for row in rows]

        # Drop columns where >60% of values are empty (sparsity threshold)
        n = len(filled_rows)
        non_sparse_keys = []
        sparse_bool_keys = []
        for k in all_keys:
            empty_count = sum(1 for row in filled_rows if _is_empty(row[k]))
            if empty_count / n <= 0.6:
                non_sparse_keys.append(k)
            else:
                # Check if the non-empty values are all boolean-like
                non_empty_vals = [str(row[k]).strip().lower() for row in filled_rows if not _is_empty(row[k])]
                if non_empty_vals and all(v in _bool_vals for v in non_empty_vals):
                    sparse_bool_keys.append(k)

        # If we have sparse boolean matrix columns, melt them into label/value pairs
        if len(sparse_bool_keys) >= 2:
            melted_rows = []
            for row in filled_rows:
                base = {k: row[k] for k in non_sparse_keys}
                for bk in sparse_bool_keys:
                    if not _is_empty(row[bk]):
                        new_row = dict(base)
                        # Use a sensible column name for the article/field key
                        label_col = "article" if any("article" in k for k in sparse_bool_keys) else "field"
                        new_row[label_col] = bk
                        new_row["status"] = str(row[bk]).strip()
                        melted_rows.append(new_row)
            if melted_rows:
                filled_rows = melted_rows
                all_keys = list(melted_rows[0].keys())
                non_sparse_keys = all_keys

        # Rebuild using non-sparse columns, skip entirely-empty rows
        normalized = []
        for row in filled_rows:
            clean = {k: row.get(k) for k in non_sparse_keys}
            if any(not _is_empty(v) for v in clean.values()):
                normalized.append(clean)

        return normalized

    def extract_from_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract structured rows from pdfplumber tables.
        Batches tables into a single Groq call to stay within rate limits."""
        # Filter out tiny or empty tables
        valid = [t for t in tables if t.get("data") and len(t["data"]) >= 2]
        if not valid:
            return []

        # Batch all tables into one prompt (max 10 tables, 10k chars total)
        sections = []
        total_chars = 0
        for tbl in valid[:10]:
            page = tbl.get("page", "?")
            lines = []
            for row in tbl["data"]:
                cells = [str(c).strip() if c is not None else "" for c in row]
                lines.append(" | ".join(cells))
            block = f"--- Table (page {page}) ---\n" + "\n".join(lines)
            if total_chars + len(block) > 10000:
                break
            sections.append(block)
            total_chars += len(block)

        if not sections:
            return []

        combined = "\n\n".join(sections)
        prompt = _TABLE_PROMPT.format(page="multiple", table_text=combined)

        try:
            raw_response = self.generate_sync(prompt, temperature=0.1, max_tokens=3000)
            raw_response = re.sub(r"^```(?:json)?\s*", "", raw_response.strip(), flags=re.IGNORECASE)
            raw_response = re.sub(r"\s*```$", "", raw_response.strip())
            parsed = json.loads(raw_response)
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                return []
            rows = [r for r in parsed if isinstance(r, dict) and r]
            return self._normalize_columns(rows) if rows else []
        except Exception as exc:
            logger.warning("groq_table_extraction_failed", extra={"error": str(exc)})
            return []

    def process_pdf_text_to_exports(
        self, text: str, csv_path: str, json_path: str
    ) -> List[Dict[str, Any]]:
        """Extract structured data and save to CSV + JSON files."""
        rows = self.extract_structured_data(text)
        if not rows:
            return []

        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)

        # Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        # Save CSV
        headers = list(rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        logger.info("groq_extraction_done", extra={"rows": len(rows)})
        return rows
