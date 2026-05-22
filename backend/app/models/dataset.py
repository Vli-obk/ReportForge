from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    schema_definition = Column(JSON, nullable=True)  # Column definitions
    row_count = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing, ready, error
    data_preview = Column(Text, nullable=True)  # JSON string with sample data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="datasets")
    pdf_document = relationship("PDFDocument", back_populates="datasets")
    data_rows = relationship("DataRow", back_populates="dataset", cascade="all, delete-orphan")
