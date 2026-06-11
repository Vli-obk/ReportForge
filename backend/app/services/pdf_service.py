import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import pdf_extract_semaphore
from app.core.config import settings
from app.core.sse import publish_job_event
from app.models.ai_summary import AISummary
from app.models.analytics import Analytics
from app.models.data_row import DataRow
from app.models.dataset import Dataset
from app.models.pdf_document import PDFDocument
from app.models.processing_job import ProcessingJob
from app.schemas.pdf_document import PDFDocumentCreate
from app.schemas.processing_job import ProcessingJobCreate
from app.scraper.pdf_scraper import PDFScraper
from app.services.ai_service import AIService
from app.services.groq_service import GroqService, GroqUnavailableError, GroqRateLimitError
from app.services.local_extractor import LocalExtractorService
from app.transformers.data_transformer import DataTransformer

logger = logging.getLogger(__name__)


def _generate_fake_pdf(url: str, save_path: str) -> None:
    """Write a minimal valid PDF with placeholder financial content when the real URL is inaccessible."""
    import fitz  # PyMuPDF

    domain = urlparse(url).netloc or "unknown source"
    path_hint = urlparse(url).path.split("/")[-1] or "document"

    fake_text = f"""ANNUAL REPORT / FINANCIAL DOCUMENT
Source: {url}

NOTE: This document could not be fetched from {domain} (access restricted).
The following is placeholder content generated for pipeline demonstration purposes.

EXECUTIVE SUMMARY
-----------------
This report covers the fiscal year ended December 31, 2022.
Total revenues: $1,245,300,000
Net income: $187,600,000
Earnings per share (diluted): $2.34
Total assets: $8,920,000,000
Total liabilities: $5,340,000,000
Stockholders equity: $3,580,000,000

REVENUE BREAKDOWN
-----------------
Product revenue:   $834,200,000   (67%)
Service revenue:   $301,500,000   (24%)
Licensing revenue: $109,600,000   ( 9%)

KEY METRICS
-----------
Gross margin: 54.2%
Operating margin: 18.7%
Return on equity: 12.4%
Debt-to-equity ratio: 0.68
Current ratio: 1.92

FORWARD-LOOKING STATEMENTS
---------------------------
The company expects revenue growth of 8-12% in the coming fiscal year,
driven by expansion in key markets and new product launches.

[PLACEHOLDER — {path_hint}]
"""

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((60, 60), fake_text, fontsize=10)
    doc.save(save_path)
    doc.close()
    logger.warning("fake_pdf_generated", extra={"url": url, "path": save_path})


_MAX_PAGES = 40


def _extract_pages_limited(scraper: "PDFScraper", pdf_path: str, max_pages: int = 40) -> dict:
    """Extract text from a PDF or plain-text file."""
    import pdfplumber
    result: dict = {"text": "", "pages": [], "metadata": {}, "tables": []}

    # Plain-text fallback (scraped HTML pages saved as .txt)
    if pdf_path.endswith(".txt"):
        with open(pdf_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        result["text"] = text
        result["metadata"]["page_count"] = 1
        result["pages"].append({"page_number": 1, "text": text})
        return result

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        result["metadata"]["page_count"] = total
        pages_to_read = min(total, max_pages)
        if total > max_pages:
            logger.info(
                "pdf_page_limit_applied",
                extra={"total_pages": total, "pages_read": pages_to_read},
            )
        for i, page in enumerate(pdf.pages[:pages_to_read]):
            page_text = page.extract_text() or ""
            result["pages"].append({"page_number": i + 1, "text": page_text})
            result["text"] += page_text + "\n\n"
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    result["tables"].append({"page": i + 1, "data": table})
    return result


class PDFService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraper = PDFScraper()
        self.transformer = DataTransformer()
        self.groq = GroqService(timeout=60)
        self.local_extractor = LocalExtractorService()

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    async def create_pdf_document(
        self, user_id: int, document_data: PDFDocumentCreate
    ) -> PDFDocument:
        file_extension = os.path.splitext(document_data.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        db_document = PDFDocument(
            user_id=user_id,
            filename=unique_filename,
            original_filename=document_data.original_filename,
            file_path=file_path,
            file_size=document_data.file_size,
            source_type=document_data.source_type,
            source_url=document_data.source_url,
            status="pending",
        )
        self.db.add(db_document)
        await self.db.commit()
        await self.db.refresh(db_document)
        return db_document

    async def get_user_documents(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[PDFDocument]:
        stmt = (
            select(PDFDocument)
            .where(PDFDocument.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def get_document(self, document_id: int, user_id: int) -> Optional[PDFDocument]:
        stmt = select(PDFDocument).where(
            PDFDocument.id == document_id,
            PDFDocument.user_id == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def delete_document(self, document_id: int, user_id: int) -> bool:
        document = await self.get_document(document_id, user_id)
        if not document:
            return False
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        await self.db.delete(document)
        await self.db.commit()
        return True

    # ------------------------------------------------------------------ #
    # Processing                                                           #
    # ------------------------------------------------------------------ #

    async def process_pdf(self, document_id: int, use_ocr: bool = False) -> PDFDocument:
        stmt = select(PDFDocument).where(PDFDocument.id == document_id)
        document = (await self.db.execute(stmt)).scalar_one_or_none()
        if not document:
            raise ValueError("Document not found")

        document.status = "processing"
        await self.db.commit()

        try:
            self.scraper.use_ocr = use_ocr
            async with pdf_extract_semaphore:
                extraction_result = await asyncio.to_thread(
                    _extract_pages_limited, self.scraper, document.file_path
                )

            document.page_count = extraction_result["metadata"].get("page_count", 0)
            document.ocr_processed = use_ocr
            document.extraction_metadata = str(extraction_result["metadata"])
            document.status = "completed"
            await self.db.commit()

            extracted_text = extraction_result.get("text", "")
            raw_tables = extraction_result.get("tables", [])
            pages_with_text = [p for p in extraction_result.get("pages", []) if p.get("text", "").strip()]

            logger.info(
                "pdf_extraction_summary",
                extra={
                    "document_id": document.id,
                    "pages": document.page_count,
                    "tables": len(raw_tables),
                    "text_chars": len(extracted_text),
                },
            )

            # NLP entity dataset — always runs regardless of structured extraction outcome
            if pages_with_text:
                try:
                    from app.services.nlp_service import extract_entities_as_rows
                    entity_rows = await asyncio.to_thread(
                        extract_entities_as_rows,
                        pages_with_text,
                        document.original_filename,
                    )
                    if entity_rows:
                        await self._create_nlp_entity_dataset(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            rows=entity_rows,
                            name=f"NLP Entities - {document.original_filename}",
                        )
                    else:
                        logger.info("nlp_entity_rows_empty", extra={"document_id": document.id})
                except Exception as exc:
                    logger.warning("nlp_entity_extraction_failed", extra={"document_id": document.id, "error": str(exc)})

            structured_data: List = []

            # Step 1: Table-aware Groq extraction (best quality — preserves structure)
            if raw_tables:
                try:
                    structured_data = await asyncio.to_thread(
                        self.groq.extract_from_tables, raw_tables
                    )
                    if structured_data:
                        await self._create_dataset_from_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=structured_data,
                            name=f"Données extraites (IA) - {document.original_filename}",
                        )
                except ValueError as exc:
                    logger.warning("groq_table_quality_rejected", extra={"document_id": document.id, "reason": str(exc)})
                    structured_data = []
                except (GroqUnavailableError, GroqRateLimitError) as exc:
                    logger.warning("groq_table_unavailable", extra={"document_id": document.id, "error": str(exc)})
                    structured_data = []
                except Exception as exc:
                    logger.warning("groq_table_failed", extra={"document_id": document.id, "error": str(exc)})
                    structured_data = []

            # Step 2: Full-text Groq extraction (fallback when no tables found)
            if not structured_data and extracted_text.strip():
                try:
                    structured_data = await asyncio.to_thread(
                        self.groq.extract_structured_data, extracted_text
                    )
                    if structured_data:
                        await self._create_dataset_from_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=structured_data,
                            name=f"Données extraites (IA) - {document.original_filename}",
                        )
                except ValueError as exc:
                    logger.warning("groq_dataset_quality_rejected", extra={"document_id": document.id, "reason": str(exc)})
                    structured_data = []
                except (GroqUnavailableError, GroqRateLimitError) as exc:
                    logger.warning("groq_unavailable_falling_back", extra={"document_id": document.id, "error": str(exc)})
                    structured_data = []
                except Exception as exc:
                    logger.warning("groq_extraction_failed", extra={"document_id": document.id, "error": str(exc)})
                    structured_data = []

            # Step 3: Local regex extractor (no API, zero cost)
            if not structured_data and extracted_text.strip():
                try:
                    structured_data = await asyncio.to_thread(
                        self.local_extractor.extract,
                        extracted_text,
                        document.original_filename,
                    )
                    if structured_data:
                        await self._create_dataset_from_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=structured_data,
                            name=f"Données extraites - {document.original_filename}",
                        )
                except ValueError as exc:
                    logger.warning("local_extraction_quality_rejected", extra={"document_id": document.id, "reason": str(exc)})
                    structured_data = []
                except Exception as exc:
                    logger.warning("local_extraction_failed", extra={"document_id": document.id, "error": str(exc)})
                    structured_data = []

            # Step 4: Raw pdfplumber table dump (no AI, last resort before text fallback)
            if not structured_data and raw_tables:
                try:
                    table_data = await asyncio.to_thread(
                        self.scraper.extract_tables_to_dataframe,
                        raw_tables,
                    )
                    if table_data:
                        await self._create_dataset_from_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=table_data,
                            name=f"Dataset from {document.original_filename}",
                        )
                        structured_data = table_data
                except ValueError as exc:
                    logger.warning(
                        "pdfplumber_dataset_quality_rejected",
                        extra={"document_id": document.id, "reason": str(exc)},
                    )
                except Exception:
                    logger.exception(
                        "pdfplumber_dataset_failed", extra={"document_id": document.id}
                    )

            # Fallback 2: one row per page when both Gemini and tables failed
            if not structured_data:
                pages = [
                    p for p in extraction_result.get("pages", [])
                    if p.get("text", "").strip()
                ]
                if pages:
                    try:
                        text_data = [
                            {
                                "page": p["page_number"],
                                "content": p["text"].strip()[:2000],
                            }
                            for p in pages
                        ]
                        await self._create_dataset_from_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=text_data,
                            name=f"Texte extrait - {document.original_filename}",
                        )
                    except ValueError as exc:
                        logger.warning(
                            "text_dataset_quality_rejected",
                            extra={"document_id": document.id, "reason": str(exc)},
                        )
                    except Exception:
                        logger.exception(
                            "text_dataset_failed", extra={"document_id": document.id}
                        )

            await self.db.commit()
            await self.db.refresh(document)
            return document

        except Exception as exc:
            await self.db.rollback()
            document.status = "failed"
            document.error_message = str(exc)
            await self.db.commit()
            raise

    # ------------------------------------------------------------------ #
    # Dataset creation                                                     #
    # ------------------------------------------------------------------ #

    async def _create_dataset_from_data(
        self, user_id: int, pdf_document_id: int, data: List, name: str
    ) -> Dataset:
        transformed_rows = self.transformer.transform_to_dataset_format(data, pdf_document_id)
        # Validate quality — raises ValueError if data is unusable; caller handles it
        self.transformer.validate_dataset([row["row_data"] for row in transformed_rows])

        # Confidence = non-null cell ratio (same logic as Gemini path)
        if transformed_rows:
            all_values = [v for r in transformed_rows for v in r["row_data"].values()]
            non_null = sum(1 for v in all_values if v not in (None, "", "nan"))
            confidence = int((non_null / len(all_values)) * 100) if all_values else 0
        else:
            confidence = 0

        logger.info(
            "dataset_creating",
            extra={"pdf_document_id": pdf_document_id, "rows": len(transformed_rows), "confidence": confidence},
        )

        dataset = Dataset(
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            name=name,
            schema_definition=self._schema_from_rows([row["row_data"] for row in transformed_rows]),
            data_preview=json.dumps([row["row_data"] for row in transformed_rows[:5]]),
            row_count=len(transformed_rows),
            status="ready",
        )
        self.db.add(dataset)
        await self.db.flush()

        if transformed_rows:
            await self.db.execute(
                insert(DataRow),
                [
                    {
                        "dataset_id": dataset.id,
                        "row_data": row["row_data"],
                        "extraction_method": row["extraction_method"],
                        "confidence_score": confidence,
                    }
                    for row in transformed_rows
                ],
            )

        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def _create_dataset_from_gemini_data(
        self,
        user_id: int,
        pdf_document_id: int,
        data: List,
        name: str,
        csv_path: str,
        json_path: str,
    ) -> Dataset:
        transformed_rows = self.transformer.transform_to_dataset_format(
            data,
            pdf_document_id,
            extraction_method="gemini",
        )
        # Raises ValueError if data doesn't meet quality bar; caller catches it
        self.transformer.validate_dataset([r["row_data"] for r in transformed_rows])

        # Confidence = non-null cell ratio
        if transformed_rows and transformed_rows[0]["row_data"]:
            num_cols = len(transformed_rows[0]["row_data"])
            total_cells = len(transformed_rows) * num_cols
            null_cells = sum(
                1
                for r in transformed_rows
                for v in r["row_data"].values()
                if v in (None, "")
            )
            calculated_confidence = int(((total_cells - null_cells) / total_cells) * 100)
        else:
            calculated_confidence = 0

        dataset = Dataset(
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            name=name,
            description=f"CSV saved to {csv_path}",
            row_count=len(transformed_rows),
            status="ready",
        )
        self.db.add(dataset)
        await self.db.flush()

        if transformed_rows:
            await self.db.execute(
                insert(DataRow),
                [
                    {
                        "dataset_id": dataset.id,
                        "row_data": row["row_data"],
                        "extraction_method": row["extraction_method"],
                        "confidence_score": calculated_confidence,
                    }
                    for row in transformed_rows
                ],
            )

        await self.db.commit()
        await self.db.refresh(dataset)
        logger.info(
            "gemini_dataset_created",
            extra={
                "pdf_document_id": pdf_document_id,
                "rows": len(transformed_rows),
                "confidence": calculated_confidence,
            },
        )
        return dataset

    async def _create_nlp_entity_dataset(
        self, user_id: int, pdf_document_id: int, rows: List, name: str
    ) -> Optional[Dataset]:
        """Create a fixed-schema NLP entity dataset. Bypasses DataTransformer."""
        if not rows:
            return None

        # Deduplicate by (entity, label, page)
        seen: set = set()
        unique_rows = []
        for r in rows:
            key = (str(r.get("entity", "")).lower(), r.get("label", ""), r.get("page", 0))
            if key not in seen:
                seen.add(key)
                unique_rows.append(r)

        if not unique_rows:
            return None

        schema = {
            "entity": "string",
            "label": "string",
            "confidence": "float",
            "page": "integer",
            "source_document": "string",
        }

        dataset = Dataset(
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            name=name,
            schema_definition=schema,
            data_preview=json.dumps(unique_rows[:5]),
            row_count=len(unique_rows),
            status="ready",
        )
        self.db.add(dataset)
        await self.db.flush()

        await self.db.execute(
            insert(DataRow),
            [
                {
                    "dataset_id": dataset.id,
                    "row_data": row,
                    "extraction_method": "nlp",
                    "confidence_score": int(row.get("confidence", 0.0) * 100),
                }
                for row in unique_rows
            ],
        )

        await self.db.commit()
        await self.db.refresh(dataset)
        logger.info(
            "nlp_entity_dataset_saved",
            extra={"pdf_document_id": pdf_document_id, "entity_count": len(unique_rows)},
        )
        return dataset

    # ------------------------------------------------------------------ #
    # Scraping                                                             #
    # ------------------------------------------------------------------ #

    async def scrape_pdf_from_url(self, user_id: int, url: str) -> PDFDocument:
        job = ProcessingJob(user_id=user_id, job_type="scrape", status="running")
        self.db.add(job)
        await self.db.commit()

        asyncio.create_task(
            publish_job_event(
                user_id=user_id,
                job_data={"job_id": str(job.id), "status": "processing", "progress": 0, "filename": url},
            )
        )

        try:
            filename = self.scraper.filename_from_url(url)
            unique_filename = f"{uuid.uuid4()}.pdf"
            file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

            try:
                await asyncio.to_thread(self.scraper.download_pdf_from_url, url, file_path)
            except (ValueError, PermissionError, FileNotFoundError, IOError) as download_exc:
                # Direct PDF download failed — try treating URL as an HTML page
                logger.info(
                    "pdf_direct_download_failed_trying_html",
                    extra={"url": url, "error": str(download_exc)},
                )
                page_text, pdf_links, page_session = await asyncio.to_thread(
                    self.scraper.fetch_html_page, url
                )
                downloaded = False
                if pdf_links:
                    # Try each PDF link in order, reusing the page session (cookies + referer)
                    for pdf_link in pdf_links[:5]:
                        try:
                            logger.info("html_pdf_link_trying", extra={"url": url, "pdf_link": pdf_link})
                            await asyncio.to_thread(
                                self.scraper.download_pdf_from_url,
                                pdf_link,
                                file_path,
                                url,        # referer = the page we scraped
                                page_session,  # reuse session with cookies
                            )
                            filename = self.scraper.filename_from_url(pdf_link)
                            downloaded = True
                            break
                        except Exception as link_exc:
                            logger.warning("html_pdf_link_failed", extra={"pdf_link": pdf_link, "error": str(link_exc)})
                            continue

                if not downloaded:
                    # No PDF found or all links failed — save the page text as .txt
                    logger.info("html_no_pdf_saving_text", extra={"url": url, "text_len": len(page_text)})
                    txt_path = file_path.replace(".pdf", ".txt")
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(page_text)
                    file_path = txt_path
                    unique_filename = os.path.basename(txt_path)

            asyncio.create_task(
                publish_job_event(
                    user_id=user_id,
                    job_data={
                        "job_id": str(job.id),
                        "status": "processing",
                        "progress": 50,
                        "filename": filename,
                    },
                )
            )

            file_size = os.path.getsize(file_path)
            document = PDFDocument(
                user_id=user_id,
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                source_type="url",
                source_url=url,
                file_size=file_size,
                status="pending",
            )
            self.db.add(document)
            await self.db.flush()

            job.status = "completed"
            job.pdf_document_id = document.id
            job.completed_at = datetime.utcnow()
            await self.db.commit()

            asyncio.create_task(
                publish_job_event(
                    user_id=user_id,
                    job_data={
                        "job_id": str(job.id),
                        "status": "done",
                        "progress": 100,
                        "filename": filename,
                    },
                )
            )
            return document

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            await self.db.commit()
            asyncio.create_task(
                publish_job_event(
                    user_id=user_id,
                    job_data={
                        "job_id": str(job.id),
                        "status": "failed",
                        "progress": 0,
                        "filename": url,
                    },
                )
            )
            raise

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _schema_from_rows(self, rows: List[dict]) -> dict:
        schema: dict = {}
        for row in rows:
            for key, value in row.items():
                if key not in schema:
                    schema[key] = type(value).__name__ if value is not None else "null"
        return schema
