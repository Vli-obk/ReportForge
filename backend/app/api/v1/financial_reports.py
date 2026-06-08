import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.deps import get_current_user
from app.core.config import settings
from app.database.session import get_db
from app.models.extraction_audit import ExtractionAudit
from app.models.financial_report import FinancialReport
from app.models.user import User
from app.schemas.financial_report import ExtractionAuditOut, FinancialReportOut, FinancialReportWithAudit
from app.services.financial_extractor import FinancialExtractor

router = APIRouter()
logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".html", ".htm"}


# ────────────────────────────────────────────────────────────────────────────
# Background worker — runs after the HTTP response is returned
# ────────────────────────────────────────────────────────────────────────────

async def _process_in_background(
    file_path: str,
    report_id: int,
    user_id: int,
    report_type: Optional[str],
) -> None:
    from app.database.session import AsyncSessionLocal
    from app.models.financial_report import FinancialReport as FR

    async with AsyncSessionLocal() as db:
        extractor = FinancialExtractor(db)
        # Re-fetch the report so we're working in the new session
        report = (
            await db.execute(select(FR).where(FR.id == report_id))
        ).scalar_one_or_none()
        if not report:
            logger.error("bg_report_not_found", extra={"report_id": report_id})
            return
        try:
            await extractor._run_pipeline(report, file_path)
        except Exception as exc:
            report.processing_status = "failed"
            report.error_message = str(exc)[:500]
            await db.commit()
            logger.exception("bg_extraction_failed", extra={"report_id": report_id})


# ────────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=FinancialReportOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_financial_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a financial report (PDF, TXT, HTML).
    Returns immediately with status='processing'; extraction runs in background.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {settings.MAX_UPLOAD_SIZE // (1024*1024)} MB",
        )

    # Persist file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Create report row (status=pending → will become processing in background)
    report = FinancialReport(
        user_id=current_user.id,
        report_type=report_type,
        processing_status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Kick off background extraction
    background_tasks.add_task(
        _process_in_background,
        file_path=file_path,
        report_id=report.id,
        user_id=current_user.id,
        report_type=report_type,
    )

    logger.info(
        "financial_report_queued",
        extra={"report_id": report.id, "filename": file.filename},
    )
    return report


@router.get("/", response_model=List[FinancialReportOut])
async def list_financial_reports(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(FinancialReport)
        .where(FinancialReport.user_id == current_user.id)
        .order_by(FinancialReport.created_at.desc())
        .offset(skip)
        .limit(min(limit, 200))
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("/{report_id}", response_model=FinancialReportWithAudit)
async def get_financial_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _get_or_404(db, report_id, current_user.id)
    return report


@router.get("/{report_id}/audit", response_model=List[ExtractionAuditOut])
async def get_audit_log(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_or_404(db, report_id, current_user.id)  # ownership check
    stmt = (
        select(ExtractionAudit)
        .where(ExtractionAudit.report_id == report_id)
        .order_by(ExtractionAudit.created_at)
    )
    return (await db.execute(stmt)).scalars().all()


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _get_or_404(db, report_id, current_user.id)
    await db.delete(report)
    await db.commit()


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, report_id: int, user_id: int) -> FinancialReport:
    stmt = select(FinancialReport).where(
        FinancialReport.id == report_id,
        FinancialReport.user_id == user_id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report
