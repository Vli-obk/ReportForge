import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

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
from app.services.gemini_service import GeminiService
from app.transformers.data_transformer import DataTransformer

logger = logging.getLogger(__name__)


_MAX_PAGES = 40


def _extract_pages_limited(scraper: "PDFScraper", pdf_path: str) -> dict:
    """Extract text from at most _MAX_PAGES pages to keep memory bounded."""
    import pdfplumber
    result: dict = {"text": "", "pages": [], "metadata": {}, "tables": []}
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        result["metadata"]["page_count"] = total
        pages_to_read = min(total, _MAX_PAGES)
        if total > _MAX_PAGES:
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
        # retries=0 so rate-limit failures are immediate rather than sleeping
        # 10 + 20 seconds per chunk and blocking the threadpool for minutes.
        self.gemini_service = GeminiService(
            base_url=settings.GEMINI_API_URL,
            model=settings.GEMINI_MODEL,
            api_key=settings.GEMINI_API_KEY,
            retries=0,
        )

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

            # Gemini structured extraction (best-effort; skips if Gemini unavailable)
            structured_data: List = []
            try:
                if extracted_text.strip():
                    csv_filename = f"{os.path.splitext(document.filename)[0]}_gemini_extracted.csv"
                    json_filename = f"{os.path.splitext(document.filename)[0]}_gemini_extracted.json"
                    csv_path = os.path.join(settings.UPLOAD_DIR, csv_filename)
                    json_path = os.path.join(settings.UPLOAD_DIR, json_filename)
                    structured_data = await asyncio.to_thread(
                        self.gemini_service.process_pdf_text_to_exports,
                        extracted_text,
                        csv_path,
                        json_path,
                    )
                    if structured_data:
                        await self._create_dataset_from_gemini_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=structured_data,
                            name=f"Gemini Extracted Data - {document.original_filename}",
                            csv_path=csv_path,
                            json_path=json_path,
                        )
            except ValueError as exc:
                logger.warning(
                    "gemini_dataset_quality_rejected",
                    extra={"document_id": document.id, "reason": str(exc)},
                )
                structured_data = []
            except Exception as exc:
                logger.warning(
                    "gemini_extraction_failed",
                    extra={"document_id": document.id, "error": str(exc)},
                )
                structured_data = []

            # Fallback: pdfplumber tables when Gemini produced nothing
            if not structured_data and extraction_result["tables"]:
                try:
                    table_data = await asyncio.to_thread(
                        self.scraper.extract_tables_to_dataframe,
                        extraction_result["tables"],
                    )
                    if table_data:
                        await self._create_dataset_from_data(
                            user_id=document.user_id,
                            pdf_document_id=document.id,
                            data=table_data,
                            name=f"Dataset from {document.original_filename}",
                        )
                except ValueError as exc:
                    logger.warning(
                        "pdfplumber_dataset_quality_rejected",
                        extra={"document_id": document.id, "reason": str(exc)},
                    )
                except Exception:
                    logger.exception(
                        "pdfplumber_dataset_failed", extra={"document_id": document.id}
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
                        "confidence_score": row["confidence_score"],
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
            extraction_method=f"gemini_{self.gemini_service.model}",
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

            await asyncio.to_thread(self.scraper.download_pdf_from_url, url, file_path)

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
