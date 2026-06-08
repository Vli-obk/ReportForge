from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PDFDocumentBase(BaseModel):
    filename: str
    original_filename: str
    source_type: str = "upload"
    source_url: Optional[str] = None


class PDFDocumentCreate(PDFDocumentBase):
    file_size: int


class PDFDocumentUpdate(BaseModel):
    status: Optional[str] = None
    page_count: Optional[int] = None
    ocr_processed: Optional[bool] = None
    error_message: Optional[str] = None


class PDFDocument(PDFDocumentBase):
    id: int
    user_id: int
    file_path: str
    file_size: int
    page_count: int
    status: str
    ocr_processed: bool
    extraction_metadata: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PDFUploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    message: str
