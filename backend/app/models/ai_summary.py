from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class AISummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True, index=True)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, nullable=False)
    classification = Column(String, nullable=True)  # e.g., Financial Report, Invoice, etc.
    entities = Column(JSON, nullable=True)  # List of key extracted items e.g., [{"key": "Company Name", "value": "Acme Inc"}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pdf_document = relationship("PDFDocument", back_populates="ai_summaries")