import asyncio
import logging
import os
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.deps import get_current_user
from app.core.config import settings
from app.database.session import AsyncSessionLocal, get_db
from app.models.ai_summary import AISummary as AISummaryModel
from app.models.analytics import Analytics as AnalyticsModel
from app.models.data_row import DataRow
from app.models.dataset import Dataset
from app.models.pdf_document import PDFDocument as PDFDocumentModel
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.schemas.ai_summary import AISummary as AISummarySchema
from app.schemas.analytics import Analytics as AnalyticsSchema
from app.schemas.gemini import GeminiExtractResponse
from app.schemas.pdf_document import PDFDocument, PDFDocumentCreate, PDFUploadResponse
from app.schemas.processing_job import Statistics
from app.services.groq_service import GroqService, GroqRateLimitError, GroqUnavailableError
from app.core.concurrency import pdf_extract_semaphore as _pdf_extract_semaphore
from app.services.pdf_service import PDFService

router = APIRouter()
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Background helpers                                                   #
# ------------------------------------------------------------------ #

async def process_pdf_background(document_id: int, use_ocr: bool) -> None:
    async with AsyncSessionLocal() as db:
        pdf_service = PDFService(db)
        try:
            await pdf_service.process_pdf(document_id, use_ocr=use_ocr)
        except Exception:
            logger.exception("pdf_background_processing_failed", extra={"document_id": document_id})


def _write_file(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def _extract_pages_limited(scraper, pdf_path: str, max_pages: int = 40) -> dict:
    """Extract text from at most max_pages pages to prevent OOM on huge PDFs."""
    import pdfplumber
    result: dict = {"text": "", "pages": [], "metadata": {}, "tables": []}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            result["metadata"]["page_count"] = total
            pages_to_read = min(total, max_pages)
            if total > max_pages:
                logger.info(
                    "pdf_page_limit_applied",
                    extra={"total_pages": total, "pages_read": pages_to_read, "path": pdf_path},
                )
            for i, page in enumerate(pdf.pages[:pages_to_read]):
                page_text = page.extract_text() or ""
                result["pages"].append({"page_number": i + 1, "text": page_text})
                result["text"] += page_text + "\n\n"
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        result["tables"].append({"page": i + 1, "data": table})
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc
    return result


# ------------------------------------------------------------------ #
# Statistics                                                           #
# ------------------------------------------------------------------ #

@router.get("/statistics/overview", response_model=Statistics)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_pdfs = (await db.execute(
        select(func.count()).select_from(PDFDocumentModel).where(PDFDocumentModel.user_id == current_user.id)
    )).scalar()
    total_rows = (await db.execute(
        select(func.count()).select_from(DataRow).join(Dataset).where(Dataset.user_id == current_user.id)
    )).scalar()
    ocr_processed = (await db.execute(
        select(func.count()).select_from(PDFDocumentModel).where(
            PDFDocumentModel.user_id == current_user.id,
            PDFDocumentModel.ocr_processed == True,
        )
    )).scalar()
    failed_jobs = (await db.execute(
        select(func.count()).select_from(ProcessingJob).where(
            ProcessingJob.user_id == current_user.id,
            ProcessingJob.status == "failed",
        )
    )).scalar()
    storage = (await db.execute(
        select(func.sum(PDFDocumentModel.file_size)).where(PDFDocumentModel.user_id == current_user.id)
    )).scalar() or 0

    return Statistics(
        total_pdfs=total_pdfs or 0,
        total_rows=total_rows or 0,
        ocr_processed=ocr_processed or 0,
        failed_jobs=failed_jobs or 0,
        storage_used=storage,
    )


@router.get("/dashboard/statistics", response_model=Statistics)
async def get_dashboard_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_statistics(current_user=current_user, db=db)


# ------------------------------------------------------------------ #
# Upload                                                               #
# ------------------------------------------------------------------ #

@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    use_ocr: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    content = await file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE:
        mb = settings.MAX_UPLOAD_SIZE // 1024 // 1024
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {mb} MB",
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid PDF (missing %PDF- header)",
        )

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(upload_dir, unique_filename)

    await asyncio.to_thread(_write_file, file_path, content)

    document = PDFDocumentModel(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        source_type="upload",
        status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    background_tasks.add_task(process_pdf_background, document.id, use_ocr)

    logger.info(
        "pdf_uploaded",
        extra={"document_id": document.id, "user_id": current_user.id, "size": len(content)},
    )
    return PDFUploadResponse(
        document_id=document.id,
        filename=document.original_filename,
        status=document.status,
        message="PDF uploaded. Processing started.",
    )


# ------------------------------------------------------------------ #
# Scrape                                                               #
# ------------------------------------------------------------------ #

@router.post("/scrape", response_model=PDFUploadResponse)
async def scrape_pdf(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    use_ocr: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://",
        )

    pdf_service = PDFService(db)
    try:
        document = await pdf_service.scrape_pdf_from_url(current_user.id, url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch PDF from URL: {exc}",
        )

    background_tasks.add_task(process_pdf_background, document.id, use_ocr)
    return PDFUploadResponse(
        document_id=document.id,
        filename=document.original_filename,
        status=document.status,
        message="PDF scraped successfully. Processing started.",
    )


# ------------------------------------------------------------------ #
# AI extract from stored PDF (powered by Groq / Llama 3.3)            #
# ------------------------------------------------------------------ #

@router.post("/{document_id}/gemini-extract", response_model=GeminiExtractResponse)
async def gemini_extract_pdf(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.status not in ("completed", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready for extraction (status: {document.status})",
        )

    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on disk. It may have been deleted.",
        )

    from app.services.pdf_service import _extract_pages_limited as _epl
    from app.scraper.pdf_scraper import PDFScraper
    scraper = PDFScraper()
    try:
        async with _pdf_extract_semaphore:
            # 30 pages: NLP needs full document coverage; Groq will only see first 10 pages' text
            extraction_result = await asyncio.to_thread(
                _epl, scraper, document.file_path, 30
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {exc}",
        )

    # Groq only processes first 10 pages for speed; NLP uses all 30
    groq_pages = extraction_result.get("pages", [])[:10]
    groq_text = "".join(p.get("text", "") for p in groq_pages).strip()
    extracted_text = groq_text or extraction_result.get("text", "").strip()
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted. Try enabling OCR for scanned documents.",
        )

    # Tables from first 10 pages only (Groq speed limit)
    raw_tables = [t for t in extraction_result.get("tables", []) if t.get("page", 1) <= 10]
    # NLP gets all 30 pages for full entity coverage
    pages_with_text = [p for p in extraction_result.get("pages", []) if p.get("text", "").strip()]
    groq = GroqService(timeout=45)
    started = time.perf_counter()
    extraction_method_used = "groq"

    # Step 1: Groq table-aware extraction
    structured_data = []
    if raw_tables:
        try:
            structured_data = await asyncio.to_thread(groq.extract_from_tables, raw_tables)
        except (GroqRateLimitError, GroqUnavailableError) as exc:
            logger.warning("gemini_extract_groq_table_skipped", extra={"document_id": document_id, "reason": str(exc)})
        except Exception as exc:
            logger.warning("gemini_extract_groq_table_failed", extra={"document_id": document_id, "error": str(exc)})

    # Step 2: Groq text extraction fallback (first 10 pages only)
    if not structured_data:
        try:
            structured_data = await asyncio.to_thread(
                groq.extract_structured_data, extracted_text[:8000]
            )
        except (GroqRateLimitError, GroqUnavailableError) as exc:
            logger.warning("gemini_extract_groq_text_skipped", extra={"document_id": document_id, "reason": str(exc)})
        except Exception as exc:
            logger.warning("gemini_extract_groq_text_failed", extra={"document_id": document_id, "error": str(exc)})

    # Step 3: Local extractor fallback (no API, always available)
    if not structured_data:
        try:
            from app.services.local_extractor import LocalExtractorService
            structured_data = LocalExtractorService().extract(extracted_text, document.original_filename)
            extraction_method_used = "local"
            logger.info("gemini_extract_used_local_fallback", extra={"document_id": document_id})
        except Exception as exc:
            logger.warning("gemini_extract_local_failed", extra={"document_id": document_id, "error": str(exc)})

    elapsed = round(time.perf_counter() - started, 3)

    # NLP entity extraction — skip if dataset already exists for this document
    _existing_nlp = await db.execute(
        select(Dataset).where(
            Dataset.pdf_document_id == document_id,
            Dataset.name == f"NLP Entities - {document.original_filename}",
        )
    )
    _nlp_exists = _existing_nlp.scalar_one_or_none() is not None

    if pages_with_text and not _nlp_exists:
        try:
            from app.services.nlp_service import extract_entities_as_rows
            entity_rows = await asyncio.to_thread(
                extract_entities_as_rows, pages_with_text, document.original_filename
            )
            if entity_rows:
                await pdf_service._create_nlp_entity_dataset(
                    user_id=current_user.id,
                    pdf_document_id=document_id,
                    rows=entity_rows,
                    name=f"NLP Entities - {document.original_filename}",
                )
        except Exception as exc:
            logger.warning(
                "gemini_extract_nlp_failed",
                extra={"document_id": document_id, "error": str(exc), "type": type(exc).__name__},
            )
            # Must rollback so the session is usable for the structured dataset creation below
            try:
                await db.rollback()
            except Exception:
                pass
    elif _nlp_exists:
        logger.info("gemini_extract_nlp_skipped_exists", extra={"document_id": document_id})

    if not structured_data:
        return GeminiExtractResponse(
            success=True,
            model="llama-3.3-70b-versatile",
            processing_time=elapsed,
            message="No structured data found in this PDF.",
        )

    dataset_name = f"AI Extracted ({extraction_method_used}) - {document.original_filename}"
    csv_filename = f"{os.path.splitext(document.filename)[0]}_ai_extract.csv"
    json_filename = f"{os.path.splitext(document.filename)[0]}_ai_extract.json"
    csv_path = os.path.join(settings.UPLOAD_DIR, csv_filename)
    json_path = os.path.join(settings.UPLOAD_DIR, json_filename)

    try:
        dataset = await pdf_service._create_dataset_from_gemini_data(
            user_id=current_user.id,
            pdf_document_id=document_id,
            data=structured_data,
            name=dataset_name,
            csv_path=csv_path,
            json_path=json_path,
        )
    except ValueError as exc:
        return GeminiExtractResponse(
            success=True,
            model="llama-3.3-70b-versatile",
            processing_time=elapsed,
            message=f"Data extracted but quality check failed: {exc}",
        )
    except Exception as exc:
        logger.error(
            "gemini_extract_dataset_failed",
            extra={
                "document_id": document_id,
                "error": str(exc),
                "type": type(exc).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset creation failed ({type(exc).__name__}): {exc}",
        )

    logger.info(
        "ai_extract_dataset_created",
        extra={"document_id": document_id, "dataset_id": dataset.id, "rows": dataset.row_count},
    )

    return GeminiExtractResponse(
        success=True,
        model="llama-3.3-70b-versatile",
        processing_time=elapsed,
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        row_count=dataset.row_count,
        message=f"Dataset created with {dataset.row_count} rows.",
    )


# ------------------------------------------------------------------ #
# List / get / delete                                                  #
# ------------------------------------------------------------------ #

@router.get("", response_model=List[PDFDocument])
async def get_pdfs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    return await pdf_service.get_user_documents(current_user.id, skip, limit)


@router.get("/{document_id}", response_model=PDFDocument)
async def get_pdf(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.delete("/{document_id}")
async def delete_pdf(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    success = await pdf_service.delete_document(document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"message": "Document deleted successfully"}


# ------------------------------------------------------------------ #
# AI summary / analytics / trigger                                     #
# ------------------------------------------------------------------ #

@router.get("/{document_id}/ai-summary", response_model=AISummarySchema)
async def get_pdf_ai_summary(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    summary = (await db.execute(
        select(AISummaryModel).where(AISummaryModel.pdf_document_id == document_id)
    )).scalar_one_or_none()

    if not summary:
        if document.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document status is '{document.status}' and AI summary is unavailable.",
            )
        try:
            from app.scraper.pdf_scraper import PDFScraper
            from app.services.ai_service import AIService

            scraper = PDFScraper()
            ai_service = AIService()
            async with _pdf_extract_semaphore:
                extraction_result = await asyncio.to_thread(
                    _extract_pages_limited, scraper, document.file_path, max_pages=40
                )
            extracted_text = extraction_result.get("text", "")

            summary_text = await asyncio.to_thread(ai_service.generate_summary, extracted_text)
            classification = await asyncio.to_thread(ai_service.classify_report, extracted_text)
            entities = await asyncio.to_thread(ai_service.extract_entities, extracted_text)

            summary = AISummaryModel(
                pdf_document_id=document.id,
                summary=summary_text,
                classification=classification,
                entities=entities,
            )
            db.add(summary)
            await db.commit()
            await db.refresh(summary)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate summary on demand: {exc}",
            )

    return summary


@router.get("/{document_id}/analytics", response_model=AnalyticsSchema)
async def get_pdf_analytics(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    analytics = (await db.execute(
        select(AnalyticsModel).where(AnalyticsModel.pdf_document_id == document_id)
    )).scalar_one_or_none()

    if not analytics:
        if document.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document status is '{document.status}' and AI analytics is unavailable.",
            )
        try:
            from app.scraper.pdf_scraper import PDFScraper
            from app.services.ai_service import AIService

            scraper = PDFScraper()
            ai_service = AIService()
            async with _pdf_extract_semaphore:
                extraction_result = await asyncio.to_thread(
                    _extract_pages_limited, scraper, document.file_path, max_pages=40
                )
            extracted_text = extraction_result.get("text", "")

            insights_data = await asyncio.to_thread(ai_service.generate_insights, extracted_text)

            analytics = AnalyticsModel(
                pdf_document_id=document.id,
                insights=insights_data.get("insights", []),
                kpis=insights_data.get("kpis", {}),
            )
            db.add(analytics)
            await db.commit()
            await db.refresh(analytics)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate analytics on demand: {exc}",
            )

    return analytics


@router.post("/{document_id}/trigger-ai", response_model=AISummarySchema)
async def trigger_pdf_ai(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document must be completed to run AI. Current: {document.status}",
        )

    try:
        from app.scraper.pdf_scraper import PDFScraper
        from app.services.ai_service import AIService

        scraper = PDFScraper()
        ai_service = AIService()
        async with _pdf_extract_semaphore:
            extraction_result = await asyncio.to_thread(
                _extract_pages_limited, scraper, document.file_path, max_pages=40
            )
        extracted_text = extraction_result.get("text", "")

        summary_text = await asyncio.to_thread(ai_service.generate_summary, extracted_text)
        classification = await asyncio.to_thread(ai_service.classify_report, extracted_text)
        entities = await asyncio.to_thread(ai_service.extract_entities, extracted_text)

        summary = (await db.execute(
            select(AISummaryModel).where(AISummaryModel.pdf_document_id == document_id)
        )).scalar_one_or_none()
        if summary:
            summary.summary = summary_text
            summary.classification = classification
            summary.entities = entities
        else:
            summary = AISummaryModel(
                pdf_document_id=document.id,
                summary=summary_text,
                classification=classification,
                entities=entities,
            )
            db.add(summary)

        insights_data = await asyncio.to_thread(ai_service.generate_insights, extracted_text)
        analytics = (await db.execute(
            select(AnalyticsModel).where(AnalyticsModel.pdf_document_id == document_id)
        )).scalar_one_or_none()
        if analytics:
            analytics.insights = insights_data.get("insights", [])
            analytics.kpis = insights_data.get("kpis", {})
        else:
            analytics = AnalyticsModel(
                pdf_document_id=document.id,
                insights=insights_data.get("insights", []),
                kpis=insights_data.get("kpis", {}),
            )
            db.add(analytics)

        await db.commit()
        await db.refresh(summary)
        return summary
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-run AI generation: {exc}",
        )
