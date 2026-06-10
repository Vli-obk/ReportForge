import asyncio
import logging

import pdfplumber
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.pdf_document import PDFDocument
from app.models.user import User
from app.services.nlp_service import extract_entities

router = APIRouter()
logger = logging.getLogger(__name__)


async def _read_pdf_text(file_path: str) -> str:
    def _read():
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:40]:
                text = page.extract_text() or ""
                pages.append(text)
        return "\n".join(pages)

    return await asyncio.to_thread(_read)


@router.get("/{pdf_id}/entities")
async def get_entities(
    pdf_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PDFDocument).where(
            PDFDocument.id == pdf_id,
            PDFDocument.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        text = await _read_pdf_text(doc.file_path)
    except Exception as exc:
        logger.warning("nlp_read_failed", extra={"pdf_id": pdf_id, "error": str(exc)})
        raise HTTPException(status_code=422, detail="Could not read PDF file")

    data = await asyncio.to_thread(extract_entities, text)
    return {
        "pdf_id": pdf_id,
        "filename": doc.original_filename,
        "text_length": len(text),
        **data,
    }
