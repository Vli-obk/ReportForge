from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProcessingJobBase(BaseModel):
    job_type: str


class ProcessingJobCreate(ProcessingJobBase):
    pdf_document_id: Optional[int] = None


class ProcessingJobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    result: Optional[str] = None
    error_message: Optional[str] = None


class ProcessingJob(ProcessingJobBase):
    id: int
    user_id: int
    pdf_document_id: Optional[int] = None
    status: str
    progress: int
    result: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Statistics(BaseModel):
    total_pdfs: int
    total_rows: int
    ocr_processed: int
    failed_jobs: int
    storage_used: int  # in bytes
