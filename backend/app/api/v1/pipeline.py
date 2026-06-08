import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.deps import get_current_user
from app.core.security import verify_token
from app.core.sse import event_generator
from app.database.session import get_db
from app.models.processing_job import ProcessingJob as ProcessingJobModel
from app.models.user import User
from app.schemas.processing_job import ProcessingJob

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/jobs", response_model=List[ProcessingJob])
async def get_processing_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ProcessingJobModel)
        .where(ProcessingJobModel.user_id == current_user.id)
        .order_by(ProcessingJobModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
async def get_processing_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProcessingJobModel).where(
        ProcessingJobModel.id == job_id,
        ProcessingJobModel.user_id == current_user.id,
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/stream")
async def stream_pipeline_events(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_token(token)
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid token")

    return StreamingResponse(
        event_generator(user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def get_pipeline_health(db: AsyncSession = Depends(get_db)):
    services: dict = {}

    # Database — real connectivity check
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "operational"
    except Exception as exc:
        services["database"] = f"error: {str(exc)[:120]}"
        logger.error("health_db_failed", extra={"error": str(exc)})

    # OCR — check tesseract binary availability
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        services["ocr"] = "operational"
    except Exception:
        services["ocr"] = "unavailable"

    # PDF scraper — pdfplumber import check
    try:
        import pdfplumber  # noqa: F401
        services["pdf_scraper"] = "operational"
    except Exception:
        services["pdf_scraper"] = "error"

    services["transformer"] = "operational"

    all_critical_ok = services.get("database") == "operational"

    return {
        "status": "healthy" if all_critical_ok else "degraded",
        "services": services,
    }
