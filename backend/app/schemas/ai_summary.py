from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime


class EntityItem(BaseModel):
    key: str
    value: str


class AISummaryBase(BaseModel):
    summary: str
    classification: Optional[str] = None
    entities: Optional[List[Dict[str, Any]]] = None


class AISummaryCreate(AISummaryBase):
    pdf_document_id: int


class AISummary(AISummaryBase):
    id: int
    pdf_document_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
