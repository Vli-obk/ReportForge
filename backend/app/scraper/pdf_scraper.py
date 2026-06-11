import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import pdfplumber
import pytesseract
import requests
from bs4 import BeautifulSoup
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

    def _make_session(self, referer: Optional[str] = None) -> requests.Session:
        parsed = urlparse(referer or "https://example.com")
        origin = f"{parsed.scheme}://{parsed.netloc}"
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": referer or (origin + "/"),
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
        })
        return session

    def download_pdf_from_url(self, url: str, save_path: str, referer: Optional[str] = None, session: Optional[requests.Session] = None) -> str:
        dir_path = os.path.dirname(save_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Use provided session (with cookies from prior page fetch) or create a fresh one
        sess = session or self._make_session(referer or url)

        last_error: Optional[Exception] = None

        for attempt, delay in enumerate(_DOWNLOAD_RETRY_DELAYS):
            if delay:
                logger.info("pdf_download_retry", extra={"url": url, "attempt": attempt + 1, "delay": delay})
                time.sleep(delay)

            try:
                response = sess.get(url, timeout=(15, 120), stream=True, allow_redirects=True)
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
                                        f"URL does not serve a valid PDF (first bytes: {chunk[:8]!r})"
                                    )
                                pdf_verified = True
                            f.write(chunk)
                            total_bytes += len(chunk)

                    if not pdf_verified:
                        raise ValueError("Empty response — URL returned no content")

                    logger.info("pdf_downloaded", extra={"url": url, "bytes": total_bytes, "path": save_path})
                    return save_path

                except Exception:
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    raise

            except requests.exceptions.Timeout as exc:
                last_error = exc
                logger.warning("pdf_download_timeout", extra={"url": url, "attempt": attempt + 1})
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
                raise
            except Exception as exc:
                last_error = exc
                logger.warning("pdf_download_error", extra={"url": url, "attempt": attempt + 1, "error": str(exc)})
                continue

        raise IOError(f"Download failed after {len(_DOWNLOAD_RETRY_DELAYS)} attempts: {last_error}")

    @staticmethod
    def filename_from_url(url: str) -> str:
        path = urlparse(url).path
        name = os.path.basename(path)
        if name.lower().endswith(".pdf") and len(name) > 4:
            return name
        return "document.pdf"

    def fetch_html_page(self, url: str) -> Tuple[str, List[str], "requests.Session"]:
        """
        Fetch a webpage and return (plain_text, pdf_links, session).
        The session carries cookies from the page visit — reuse it to download PDFs
        so the server sees a consistent browser session (avoids 403s on CDN-protected PDFs).
        """
        session = self._make_session(url)
        response = session.get(url, timeout=(10, 30), allow_redirects=True)
        response.raise_for_status()

        # Update referer to the final URL after redirects
        session.headers.update({"Referer": response.url})

        soup = BeautifulSoup(response.text, "html.parser")

        # Collect PDF links
        pdf_links: List[str] = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            abs_href = urljoin(url, href)
            if abs_href.lower().endswith(".pdf") or "/pdf" in abs_href.lower():
                if abs_href not in pdf_links:
                    pdf_links.append(abs_href)

        # Also check <iframe>, <embed>, <object> src attributes
        for tag in soup.find_all(["iframe", "embed", "object"], src=True):
            src = tag.get("src", "").strip()
            abs_src = urljoin(url, src)
            if ".pdf" in abs_src.lower() and abs_src not in pdf_links:
                pdf_links.append(abs_src)

        # Extract readable text
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)

        logger.info("html_page_fetched", extra={"url": url, "pdf_links": len(pdf_links), "text_len": len(text)})
        return text, pdf_links, session

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

            raw_headers = table_data[0]

            # Validate: real column labels have ≤3 words and ≤50 chars.
            # A 3-word header like "Net Income" or "Q1 2023" is fine;
            # "Bureau of Labor Statistics" (4 words) or "Employment Situation Summary
            # United States" (5 words) are document text masquerading as headers.
            # Stop-word check: 3-word strings containing "of/the/and/for/from/by/with"
            # are also likely title phrases, not column labels.
            import re as _re
            _STOP = _re.compile(r'\b(of|the|and|for|from|with|by|as|at|in|on|to)\b', _re.I)

            def _is_label(h: Any) -> bool:
                s = str(h).strip() if h else ""
                words = s.split()
                if len(words) > 3 or len(s) > 50:
                    return False
                if len(words) == 3 and _STOP.search(s):
                    return False
                # Reject pure-numeric cells — years and page numbers are not column headers
                if _re.match(r'^\d+$', s):
                    return False
                # Reject cells that are mostly digits (e.g. "2026p", "2025u", "3a")
                if len(s) <= 6 and s and sum(c.isdigit() for c in s) / len(s) >= 0.6:
                    return False
                return True

            if all(_is_label(h) for h in raw_headers):
                headers = raw_headers
                rows = table_data[1:]
            else:
                logger.debug(
                    "table_header_row_looks_like_content_using_generic_names",
                    extra={"sample": str(raw_headers[:3])},
                )
                headers = [f"column_{i+1}" for i in range(len(raw_headers))]
                rows = table_data  # first row is data, not a header

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
