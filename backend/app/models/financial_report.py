from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class FinancialReport(Base):
    __tablename__ = "financial_reports"

    id = Column(Integer, primary_key=True, index=True)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    report_type = Column(String(50), nullable=True)   # annual, quarterly, sec_filing, investor
    company_name = Column(String(255), nullable=True)
    fiscal_year = Column(String(20), nullable=True)
    currency = Column(String(10), default="USD")

    # Income Statement
    revenue = Column(Float, nullable=True)
    gross_profit = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)

    # Balance Sheet
    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    shareholders_equity = Column(Float, nullable=True)

    # Cash Flow
    operating_cash_flow = Column(Float, nullable=True)
    investing_cash_flow = Column(Float, nullable=True)
    financing_cash_flow = Column(Float, nullable=True)

    source_pages = Column(JSON, default=list)
    confidence_score = Column(Float, default=0.0)
    processing_status = Column(String(30), default="pending")
    error_message = Column(Text, nullable=True)
    extraction_timestamp = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="financial_reports")
    audit_logs = relationship(
        "ExtractionAudit", back_populates="report", cascade="all, delete-orphan"
    )
