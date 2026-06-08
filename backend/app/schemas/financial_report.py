from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class ExtractionAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step: str
    model_used: Optional[str] = None
    input_chars: int
    chunks_processed: int
    chunks_relevant: int
    duration_ms: int
    anomalies: List[str] = Field(default_factory=list)
    created_at: datetime


class FinancialReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pdf_document_id: Optional[int] = None
    user_id: int
    report_type: Optional[str] = None
    company_name: Optional[str] = None
    fiscal_year: Optional[str] = None
    currency: Optional[str] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    shareholders_equity: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    source_pages: List[int] = Field(default_factory=list)
    confidence_score: float = 0.0
    processing_status: str
    error_message: Optional[str] = None
    extraction_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FinancialReportWithAudit(FinancialReportOut):
    audit_logs: List[ExtractionAuditOut] = Field(default_factory=list)
