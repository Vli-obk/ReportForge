from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class PDFDocument(Base):
    __tablename__ = "pdf_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    page_count = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    source_type = Column(String, default="upload")  # upload, url
    source_url = Column(String, nullable=True)
    ocr_processed = Column(Boolean, default=False)
    extraction_metadata = Column(Text, nullable=True)  # JSON string
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="pdf_documents")
    datasets = relationship("Dataset", back_populates="pdf_document", cascade="all, delete-orphan")
    ai_summaries = relationship("AISummary", back_populates="pdf_document", cascade="all, delete-orphan")
    analytics_records = relationship("Analytics", back_populates="pdf_document", cascade="all, delete-orphan")

