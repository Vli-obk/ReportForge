from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False)
    insights = Column(JSON, nullable=True)  # List of insight/recommendation strings
    kpis = Column(JSON, nullable=True)  # Dictionary of key performance indicators
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pdf_document = relationship("PDFDocument", back_populates="analytics_records")
