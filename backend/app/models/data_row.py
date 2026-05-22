from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class DataRow(Base):
    __tablename__ = "data_rows"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    row_data = Column(JSON, nullable=False)  # The actual extracted data
    page_number = Column(Integer, nullable=True)
    extraction_method = Column(String, default="pdfplumber")  # pdfplumber, ocr
    confidence_score = Column(Integer, nullable=True)  # For OCR
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("Dataset", back_populates="data_rows")
