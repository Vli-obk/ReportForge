from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    pdf_document_id: int


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class Dataset(DatasetBase):
    id: int
    user_id: int
    pdf_document_id: int
    schema_definition: Optional[Dict[str, Any]] = None
    row_count: int
    status: str
    data_preview: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataRowBase(BaseModel):
    row_data: dict
    page_number: Optional[int] = None
    extraction_method: str = "pdfplumber"
    confidence_score: Optional[int] = None


class DataRow(DataRowBase):
    id: int
    dataset_id: int
    created_at: datetime

    class Config:
        from_attributes = True
