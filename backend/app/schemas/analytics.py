from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime


class AnalyticsBase(BaseModel):
    insights: Optional[List[str]] = None
    kpis: Optional[Dict[str, Any]] = None


class AnalyticsCreate(AnalyticsBase):
    pdf_document_id: int


class Analytics(AnalyticsBase):
    id: int
    pdf_document_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
