from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class ExtractionAudit(Base):
    __tablename__ = "extraction_audit"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("financial_reports.id"), nullable=False)

    step = Column(String(50), nullable=False)  # extraction, classification, gemini_extraction, validation
    model_used = Column(String(100), nullable=True)
    input_chars = Column(Integer, default=0)
    chunks_processed = Column(Integer, default=0)
    chunks_relevant = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    anomalies = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("FinancialReport", back_populates="audit_logs")
