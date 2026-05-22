from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database.session import get_db
from app.schemas.processing_job import ProcessingJob
from app.models.processing_job import ProcessingJob as ProcessingJobModel
from app.models.user import User
from app.api.deps import get_current_user
from app.core.sse import event_generator
from app.core.security import verify_token

router = APIRouter()


@router.get("/jobs", response_model=List[ProcessingJob])
async def get_processing_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all processing jobs for current user"""
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
    db: AsyncSession = Depends(get_db)
):
    """Get a specific processing job"""
    stmt = select(ProcessingJobModel).where(
        ProcessingJobModel.id == job_id,
        ProcessingJobModel.user_id == current_user.id
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    
    if not job:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.get("/stream")
async def stream_pipeline_events(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Stream real-time pipeline events via SSE"""
    user_id = verify_token(token)
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid token")

    return StreamingResponse(
        event_generator(user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/health")
def get_pipeline_health():
    """Get pipeline health status"""
    return {
        "status": "healthy",
        "services": {
            "pdf_scraper": "operational",
            "ocr": "operational",
            "database": "operational",
            "transformer": "operational"
        }
    }
