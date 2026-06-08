import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.extraction_audit import ExtractionAudit
from app.models.financial_report import FinancialReport
from app.services.data_quality import DataQualityChecker, QualityResult
from app.services.gemini_service import GeminiError, GeminiService
from app.services.section_classifier import Section, SectionClassifier
from app.services.text_cleaner import CleanedDocument, TextCleaner
from app.services.value_normalizer import ValueNormalizer

logger = logging.getLogger(__name__)

# Gemini Flash has a 1M token window — 80k chars ≈ 20k tokens, plenty of headroom
_MAX_GEMINI_INPUT_CHARS = 80_000
# First N pages always included: cover page, period info, currency/unit declaration
_CONTEXT_PAGES = 5
_CHUNK_SIZE = 4_000
_CHUNK_OVERLAP = 300

# Reporting unit → base multiplier
_UNIT_MULT: Dict[str, float] = {
    "trillions": 1_000_000_000_000.0,
    "trillion": 1_000_000_000_000.0,
    "billions": 1_000_000_000.0,
    "billion": 1_000_000_000.0,
    "millions": 1_000_000.0,
    "million": 1_000_000.0,
    "thousands": 1_000.0,
    "thousand": 1_000.0,
}

_FINANCIAL_FIELDS = frozenset({
    "revenue", "gross_profit", "operating_income", "net_income", "ebitda",
    "total_assets", "total_liabilities", "shareholders_equity",
    "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
})

_EXTRACTION_PROMPT = """You are a financial data extraction engine. Your job is to read a financial report and return a single JSON object with exact values.

━━━ STEP 1 — Detect the reporting unit ━━━
Find phrases like "in millions", "in thousands of USD", "amounts expressed in millions".
Store it in "reporting_unit" (e.g. "millions", "thousands", "billions", or "" if amounts are already in base currency).
You MUST return the raw numbers exactly as they appear in the document — do NOT multiply them yourself.
The system will apply the multiplier after parsing.

━━━ STEP 2 — Identify the company ━━━
Look in the cover page, document header, and title:
  • company_name: the legal entity (e.g. "Apple Inc.", "LVMH Moët Hennessy")
  • fiscal_year: the period (e.g. "2024", "FY2024", "Q4 2024", "Year ended December 31, 2024")
  • currency: ISO code (e.g. "USD", "EUR", "GBP")

━━━ STEP 3 — Extract financial metrics ━━━
Look in consolidated income statements, balance sheets, and cash flow statements.
Take the CONSOLIDATED / GROUP-LEVEL numbers (not subsidiary or segment-only figures).
For each metric, look for ALL alternative names listed:

  revenue              → Net revenue, Total revenue, Net sales, Total net sales, Revenues
  gross_profit         → Gross profit, Gross margin
  operating_income     → Operating income, Operating profit, Income from operations, EBIT
  net_income           → Net income, Net earnings, Net profit, Profit for the period, Net loss (negative)
  ebitda               → EBITDA, Adjusted EBITDA (only if explicitly reported)
  total_assets         → Total assets
  total_liabilities    → Total liabilities
  shareholders_equity  → Total shareholders' equity, Stockholders' equity, Total equity, Net assets
  operating_cash_flow  → Net cash from operating activities, Cash provided by operations
  investing_cash_flow  → Net cash used in investing activities (usually negative)
  financing_cash_flow  → Net cash from/used in financing activities

━━━ OUTPUT RULES ━━━
1. Return ONLY valid JSON — no markdown fences, no prose, no comments.
2. Use null for any value not present in the document.
3. NEVER estimate or infer values — only use numbers explicitly stated.
4. Return raw numbers as they appear: if document says "10,520" under "in millions", return 10520.
5. Losses must be negative numbers (not in parentheses).
6. source_pages: list the page numbers where you found financial data.
7. reporting_unit: use lowercase singular ("million", "thousand", "billion") or "" if base currency.

OUTPUT FORMAT (JSON only, no other text):
{
  "company_name": "",
  "fiscal_year": "",
  "currency": "",
  "reporting_unit": "",
  "revenue": null,
  "gross_profit": null,
  "operating_income": null,
  "net_income": null,
  "ebitda": null,
  "total_assets": null,
  "total_liabilities": null,
  "shareholders_equity": null,
  "operating_cash_flow": null,
  "investing_cash_flow": null,
  "financing_cash_flow": null,
  "source_pages": []
}

━━━ DOCUMENT TEXT ━━━
{text}"""


class FinancialExtractor:
    """
    End-to-end financial report extraction pipeline.

    Steps:
      1. Extract raw text per page (PyMuPDF → pdfplumber fallback, TXT, HTML)
      2. Clean: remove headers/footers/page-numbers/TOC/disclaimers/duplicates
      3. Build Gemini input:
           - Always include first 5 pages (cover/intro) for company identity + reporting unit
           - Include ALL Income Statement, Balance Sheet, Cash Flow chunks
           - Cap at 80k chars (~20k tokens)
      4. Gemini call (temperature=0, topP=0.1, JSON-only), up to 3 retries
      5. Apply reporting-unit multiplier (e.g. ×1_000_000 when "in millions")
      6. Value normalization for any remaining string values
      7. Data quality checks + duplicate detection
      8. Persist results and audit log
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cleaner = TextCleaner()
        self.classifier = SectionClassifier()
        self.normalizer = ValueNormalizer()
        self.quality = DataQualityChecker()
        self.gemini = GeminiService(model=settings.GEMINI_MODEL, retries=2)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def process_file(
        self,
        file_path: str,
        user_id: int,
        pdf_document_id: Optional[int] = None,
        report_type: Optional[str] = None,
    ) -> FinancialReport:
        report = FinancialReport(
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            report_type=report_type,
            processing_status="processing",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        try:
            await self._run_pipeline(report, file_path)
        except Exception as exc:
            report.processing_status = "failed"
            report.error_message = str(exc)[:500]
            await self.db.commit()
            logger.exception("financial_extractor_failed", extra={"report_id": report.id})
            raise

        return report

    # ------------------------------------------------------------------ #
    # Pipeline                                                             #
    # ------------------------------------------------------------------ #

    async def _run_pipeline(self, report: FinancialReport, file_path: str) -> None:
        # Step 1: Extract text per page
        t0 = time.perf_counter()
        page_texts = await asyncio.to_thread(self._extract_pages, file_path)
        extract_ms = int((time.perf_counter() - t0) * 1000)

        # Step 2: Clean (headers/footers/TOC/duplicates)
        cleaned: CleanedDocument = self.cleaner.clean_pages(page_texts)
        await self._audit(
            report_id=report.id,
            step="extraction",
            input_chars=sum(len(t) for t in page_texts.values()),
            chunks_processed=len(page_texts),
            chunks_relevant=len(cleaned.source_pages),
            duration_ms=extract_ms,
        )

        # Step 3: Classify chunks to find financial sections
        t1 = time.perf_counter()
        chunks = self._split(cleaned.text)
        classified = self.classifier.classify_chunks(chunks)
        relevant = [(c, cls) for c, cls in classified if SectionClassifier.is_relevant(cls)]
        classify_ms = int((time.perf_counter() - t1) * 1000)
        await self._audit(
            report_id=report.id,
            step="classification",
            input_chars=len(cleaned.text),
            chunks_processed=len(chunks),
            chunks_relevant=len(relevant),
            duration_ms=classify_ms,
        )

        # Step 4: Build Gemini input (intro context + all financial sections)
        gemini_input = self._build_gemini_input(page_texts, cleaned, relevant)

        # Step 5: Gemini extraction
        t2 = time.perf_counter()
        raw = await self._gemini_extract(gemini_input)
        gemini_ms = int((time.perf_counter() - t2) * 1000)
        await self._audit(
            report_id=report.id,
            step="gemini_extraction",
            model_used=self.gemini.model,
            input_chars=len(gemini_input),
            chunks_processed=len(relevant),
            chunks_relevant=1 if any(raw.get(f) for f in _FINANCIAL_FIELDS) else 0,
            duration_ms=gemini_ms,
        )

        # Step 6: Apply reporting-unit multiplier, then normalize remaining strings
        raw = self._apply_reporting_unit(raw)
        normalized = self.normalizer.normalize_dict(raw)

        # Step 7: Quality check + duplicate detection
        qr = self.quality.check(normalized)
        dup_id = await self._find_duplicate(
            normalized.get("company_name"), normalized.get("fiscal_year"), report.id
        )
        if dup_id:
            qr.add_warning(f"Possible duplicate of report id={dup_id}")

        await self._audit(
            report_id=report.id,
            step="validation",
            anomalies=qr.anomalies + qr.warnings,
        )

        # Step 8: Persist
        await self._save_metrics(report, normalized, qr, cleaned.source_pages)

    # ------------------------------------------------------------------ #
    # Gemini input construction                                            #
    # ------------------------------------------------------------------ #

    def _build_gemini_input(
        self,
        raw_page_texts: Dict[int, str],
        cleaned: CleanedDocument,
        relevant_chunks: List[Tuple],
    ) -> str:
        """
        Combine intro pages (for company/year/unit context) with all classified
        financial sections. Intro pages are taken from raw (uncleaned) text so
        that the company name and period line aren't stripped as repeated headers.
        """
        parts: List[str] = []
        total_chars = 0

        # Always include the first _CONTEXT_PAGES raw pages
        # (cover page has company name, report date, currency, "in millions" declaration)
        intro_pages = sorted(p for p in raw_page_texts if p <= _CONTEXT_PAGES)
        if intro_pages:
            intro_text = "\n\n".join(raw_page_texts[p] for p in intro_pages)
            parts.append(f"[DOCUMENT CONTEXT — Pages {intro_pages[0]}–{intro_pages[-1]}]\n{intro_text}")
            total_chars += len(intro_text)

        # Add all relevant financial chunks (Income Stmt, Balance Sheet, Cash Flow)
        # Keep document order (not priority order) so Gemini sees a coherent flow
        for chunk, cls in relevant_chunks:
            if total_chars + len(chunk) > _MAX_GEMINI_INPUT_CHARS:
                break
            parts.append(f"[{cls.section.value.upper()}]\n{chunk}")
            total_chars += len(chunk)

        logger.info(
            "gemini_input_built",
            extra={
                "total_chars": total_chars,
                "intro_pages": len(intro_pages),
                "financial_chunks": len(relevant_chunks),
            },
        )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # Gemini call                                                          #
    # ------------------------------------------------------------------ #

    async def _gemini_extract(self, gemini_input: str) -> dict:
        if not gemini_input.strip():
            return self._empty()

        prompt = _EXTRACTION_PROMPT.format(text=gemini_input)

        for attempt in range(3):
            try:
                raw_json = await asyncio.to_thread(
                    self.gemini._generate_json_sync,
                    prompt,
                    0.0,   # temperature — fully deterministic
                    4096,  # max output tokens — enough for all fields + source_pages
                )
                parsed = self._parse_json(raw_json)
                if parsed is not None:
                    return parsed
                logger.warning("gemini_invalid_json_retry", extra={"attempt": attempt + 1})
            except GeminiError as exc:
                logger.warning(
                    "gemini_financial_error",
                    extra={"attempt": attempt + 1, "error": str(exc)},
                )
                if attempt == 2:
                    break
                await asyncio.sleep(3)

        return self._empty()

    # ------------------------------------------------------------------ #
    # Reporting unit multiplier                                            #
    # ------------------------------------------------------------------ #

    def _apply_reporting_unit(self, data: dict) -> dict:
        """
        If Gemini detected "in millions" etc., multiply all raw numeric metric
        values by the corresponding factor before value normalization.
        Example: reporting_unit="million", revenue=10520 → revenue=10_520_000_000
        """
        unit_raw = str(data.get("reporting_unit", "")).lower().strip()
        # Accept "millions" or "million", "thousands" or "thousand", etc.
        unit_key = unit_raw.rstrip("s") + "s" if unit_raw else ""
        mult = _UNIT_MULT.get(unit_raw) or _UNIT_MULT.get(unit_key, 1.0)

        if mult == 1.0:
            return data

        out = dict(data)
        for field in _FINANCIAL_FIELDS:
            val = out.get(field)
            if isinstance(val, (int, float)) and val is not None:
                out[field] = val * mult
        return out

    # ------------------------------------------------------------------ #
    # Text extraction                                                      #
    # ------------------------------------------------------------------ #

    def _extract_pages(self, file_path: str) -> Dict[int, str]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt":
            return self._from_txt(file_path)
        if ext in (".html", ".htm"):
            return self._from_html(file_path)
        try:
            return self._from_pymupdf(file_path)
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("pymupdf_failed", extra={"error": str(exc)})
        return self._from_pdfplumber(file_path)

    def _from_pymupdf(self, path: str) -> Dict[int, str]:
        import fitz
        out: Dict[int, str] = {}
        with fitz.open(path) as doc:
            for i, page in enumerate(doc, 1):
                text = page.get_text("text")
                if text.strip():
                    out[i] = text
        return out

    def _from_pdfplumber(self, path: str) -> Dict[int, str]:
        import pdfplumber
        out: Dict[int, str] = {}
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    out[i] = text
        return out

    def _from_txt(self, path: str) -> Dict[int, str]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return {1: f.read()}

    def _from_html(self, path: str) -> Dict[int, str]:
        try:
            from bs4 import BeautifulSoup
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return {1: soup.get_text(separator="\n")}
        except ImportError:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            return {1: re.sub(r"<[^>]+>", " ", raw)}

    # ------------------------------------------------------------------ #
    # Chunking                                                             #
    # ------------------------------------------------------------------ #

    def _split(self, text: str) -> List[str]:
        if not text.strip():
            return []
        if len(text) <= _CHUNK_SIZE:
            return [text]
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + _CHUNK_SIZE, len(text))
            if end < len(text):
                boundary = text.rfind("\n\n", start, end)
                if boundary > start + _CHUNK_SIZE // 3:
                    end = boundary + 2
            chunks.append(text[start:end])
            start = end - _CHUNK_OVERLAP
        return [c for c in chunks if c.strip()]

    # ------------------------------------------------------------------ #
    # JSON parsing                                                         #
    # ------------------------------------------------------------------ #

    def _parse_json(self, raw: str) -> Optional[dict]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
            raw = re.sub(r"```$", "", raw).strip()
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _empty() -> dict:
        return {
            "company_name": None, "fiscal_year": None, "currency": None,
            "reporting_unit": "",
            "revenue": None, "gross_profit": None, "operating_income": None,
            "net_income": None, "ebitda": None,
            "total_assets": None, "total_liabilities": None, "shareholders_equity": None,
            "operating_cash_flow": None, "investing_cash_flow": None,
            "financing_cash_flow": None, "source_pages": [],
        }

    # ------------------------------------------------------------------ #
    # Duplicate detection                                                  #
    # ------------------------------------------------------------------ #

    async def _find_duplicate(
        self, company: Optional[str], fy: Optional[str], current_id: int
    ) -> Optional[int]:
        if not company or not fy:
            return None
        stmt = select(FinancialReport).where(
            FinancialReport.company_name == company,
            FinancialReport.fiscal_year == fy,
            FinancialReport.processing_status == "completed",
            FinancialReport.id != current_id,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        return existing.id if existing else None

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    async def _save_metrics(
        self,
        report: FinancialReport,
        m: dict,
        qr: QualityResult,
        source_pages: List[int],
    ) -> None:
        report.company_name = m.get("company_name")
        report.fiscal_year = m.get("fiscal_year")
        report.currency = m.get("currency") or "USD"
        report.revenue = m.get("revenue")
        report.gross_profit = m.get("gross_profit")
        report.operating_income = m.get("operating_income")
        report.net_income = m.get("net_income")
        report.ebitda = m.get("ebitda")
        report.total_assets = m.get("total_assets")
        report.total_liabilities = m.get("total_liabilities")
        report.shareholders_equity = m.get("shareholders_equity")
        report.operating_cash_flow = m.get("operating_cash_flow")
        report.investing_cash_flow = m.get("investing_cash_flow")
        report.financing_cash_flow = m.get("financing_cash_flow")
        report.source_pages = m.get("source_pages") or source_pages
        report.confidence_score = qr.confidence_score
        report.processing_status = "completed"
        report.extraction_timestamp = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)

    async def _audit(
        self,
        report_id: int,
        step: str,
        model_used: Optional[str] = None,
        input_chars: int = 0,
        chunks_processed: int = 0,
        chunks_relevant: int = 0,
        duration_ms: int = 0,
        anomalies: Optional[List[str]] = None,
    ) -> None:
        self.db.add(
            ExtractionAudit(
                report_id=report_id,
                step=step,
                model_used=model_used,
                input_chars=input_chars,
                chunks_processed=chunks_processed,
                chunks_relevant=chunks_relevant,
                duration_ms=duration_ms,
                anomalies=anomalies or [],
            )
        )
        await self.db.commit()
