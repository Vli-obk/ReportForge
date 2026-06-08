import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pdfplumber
import pytesseract
import requests
from PIL import Image

logger = logging.getLogger(__name__)

_DOWNLOAD_RETRY_DELAYS = (0, 2, 6)  # seconds before each attempt


class PDFScraper:
    def __init__(self, use_ocr: bool = False):
        self.use_ocr = use_ocr

    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {"text": "", "pages": [], "metadata": {}, "tables": []}
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["metadata"]["page_count"] = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    page_data: Dict[str, Any] = {
                        "page_number": i + 1,
                        "text": page_text,
                        "tables": [],
                    }
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            page_data["tables"].append(table)
                            result["tables"].append({"page": i + 1, "data": table})

                    if not page_text.strip() and self.use_ocr:
                        ocr_text = self._extract_ocr_from_page(page)
                        page_data["text"] = ocr_text
                        page_data["extraction_method"] = "ocr"
                    else:
                        page_data["extraction_method"] = "pdfplumber"

                    result["pages"].append(page_data)
                    result["text"] += page_data["text"] + "\n\n"

        except Exception as exc:
            raise RuntimeError(f"PDF extraction failed: {exc}") from exc

        logger.info(
            "pdf_extracted",
            extra={
                "path": pdf_path,
                "pages": result["metadata"].get("page_count", 0),
                "text_length": len(result["text"]),
                "tables": len(result["tables"]),
            },
        )
        return result

    def _extract_ocr_from_page(self, page) -> str:
        try:
            img = page.to_image()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            text = pytesseract.image_to_string(Image.open(buf))
            return text
        except Exception as exc:
            logger.warning("ocr_page_failed", extra={"error": str(exc)})
            return ""

    def download_pdf_from_url(self, url: str, save_path: str) -> str:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": origin + "/",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
        }

        dir_path = os.path.dirname(save_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        last_error: Optional[Exception] = None
        # Persistent session preserves cookies across redirects (handles cookie-wall challenges)
        session = requests.Session()
        session.headers.update(headers)

        for attempt, delay in enumerate(_DOWNLOAD_RETRY_DELAYS):
            if delay:
                logger.info(
                    "pdf_download_retry",
                    extra={"url": url, "attempt": attempt + 1, "delay": delay},
                )
                time.sleep(delay)

            try:
                response = session.get(
                    url,
                    timeout=(15, 120),
                    stream=True,
                    allow_redirects=True,
                )
                response.raise_for_status()

                try:
                    with open(save_path, "wb") as f:
                        pdf_verified = False
                        total_bytes = 0
                        for chunk in response.iter_content(chunk_size=65536):
                            if not chunk:
                                continue
                            if not pdf_verified:
                                if not chunk.startswith(b"%PDF-"):
                                    raise ValueError(
                                        f"URL does not serve a valid PDF "
                                        f"(first bytes: {chunk[:8]!r})"
                                    )
                                pdf_verified = True
                            f.write(chunk)
                            total_bytes += len(chunk)

                    if not pdf_verified:
                        raise ValueError("Empty response — URL returned no content")

                    logger.info(
                        "pdf_downloaded",
                        extra={"url": url, "bytes": total_bytes, "path": save_path},
                    )
                    return save_path

                except Exception:
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    raise

            except requests.exceptions.Timeout as exc:
                last_error = exc
                logger.warning(
                    "pdf_download_timeout",
                    extra={"url": url, "attempt": attempt + 1},
                )
                continue

            except requests.exceptions.SSLError as exc:
                raise IOError(f"SSL certificate error fetching {url}: {exc}") from exc

            except requests.exceptions.HTTPError as exc:
                sc = exc.response.status_code if exc.response is not None else 0
                if sc == 404:
                    raise FileNotFoundError(f"PDF not found at URL (404): {url}") from exc
                if sc == 403:
                    raise PermissionError(f"Access denied to PDF (403): {url}") from exc
                raise IOError(f"HTTP {sc} fetching PDF: {url}") from exc

            except (ValueError, FileNotFoundError, PermissionError, IOError):
                raise  # non-retriable

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "pdf_download_error",
                    extra={"url": url, "attempt": attempt + 1, "error": str(exc)},
                )
                continue

        raise IOError(
            f"Download failed after {len(_DOWNLOAD_RETRY_DELAYS)} attempts: {last_error}"
        )

    @staticmethod
    def filename_from_url(url: str) -> str:
        path = urlparse(url).path
        name = os.path.basename(path)
        if name.lower().endswith(".pdf") and len(name) > 4:
            return name
        return "document.pdf"

    def extract_tables_to_dataframe(self, tables: List[List]) -> List[Dict[str, Any]]:
        structured_data: List[Dict[str, Any]] = []

        for table_info in tables:
            table_data = table_info["data"]
            if not table_data:
                continue

            amrts_rows = self._extract_amrts_cv_rows(table_data)
            if amrts_rows:
                structured_data.extend(amrts_rows)
                continue

            headers = table_data[0]
            rows = table_data[1:]

            for row in rows:
                if len(row) == len(headers):
                    row_dict = {
                        str(header): row[i] if i < len(row) else None
                        for i, header in enumerate(headers)
                        if header
                    }
                    if row_dict:
                        structured_data.append(row_dict)

        return structured_data

    def _extract_amrts_cv_rows(self, table_data: List[List[Any]]) -> List[Dict[str, Any]]:
        if len(table_data) < 3:
            return []

        first_row = [self._cell_text(cell).lower() for cell in table_data[0]]
        if not (
            any("kind of business" in cell for cell in first_row)
            and any("median" in cell and "cv" in cell for cell in first_row)
            and any("standard error" in cell for cell in first_row)
        ):
            return []

        packed_row = next(
            (
                row
                for row in table_data[1:]
                if row and self._cell_text(row[0]) and "\n" in self._cell_text(row[0])
            ),
            None,
        )
        if not packed_row or len(packed_row) < 6:
            return []

        businesses = self._split_business_names(packed_row[0])
        value_columns = [self._split_value_tokens(cell) for cell in packed_row[1:6]]
        row_count = min([len(businesses), *[len(values) for values in value_columns]])
        if row_count == 0:
            return []

        columns = [
            "kind_of_business",
            "median_cv",
            "standard_error_previous_mo_to_current_mo",
            "standard_error_previous_qtr_to_current_qtr",
            "standard_error_current_mo_to_same_mo_last_yr",
            "average_revision",
        ]

        return [
            {
                columns[0]: businesses[index],
                columns[1]: value_columns[0][index],
                columns[2]: value_columns[1][index],
                columns[3]: value_columns[2][index],
                columns[4]: value_columns[3][index],
                columns[5]: value_columns[4][index],
            }
            for index in range(row_count)
        ]

    def _split_business_names(self, value: Any) -> List[str]:
        names = []
        pending: List[str] = []

        for raw_line in self._cell_text(value).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            pending.append(line)
            if not self._has_business_leader(line):
                continue
            names.append(self._clean_business_name(" ".join(pending)))
            pending = []

        if pending:
            names.append(self._clean_business_name(" ".join(pending)))

        return [name for name in names if name]

    def _split_value_tokens(self, value: Any) -> List[str]:
        return re.findall(r"-?\d+(?:\.\d+)?|\([A-Z*]+\)", self._cell_text(value))

    def _clean_business_name(self, value: str) -> str:
        value = re.sub(r"[Е….]+", " ", value)
        return re.sub(r"\s+", " ", value).strip(" ,")

    def _cell_text(self, value: Any) -> str:
        return "" if value is None else str(value)

    def _has_business_leader(self, value: str) -> bool:
        return "Е" in value or "…" in value or bool(re.search(r"\.{2,}", value))
