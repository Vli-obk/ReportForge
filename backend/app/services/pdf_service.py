from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pdf_document import PDFDocument
from app.models.dataset import Dataset
from app.models.data_row import DataRow
from app.models.processing_job import ProcessingJob
from app.models.ai_summary import AISummary
from app.models.analytics import Analytics
from app.schemas.pdf_document import PDFDocumentCreate, PDFDocumentUpdate
from app.schemas.processing_job import ProcessingJobCreate
from app.scraper.pdf_scraper import PDFScraper
from app.transformers.data_transformer import DataTransformer
from app.services.ai_service import AIService
from app.core.sse import publish_job_event
from typing import List, Optional
import os
import uuid
from datetime import datetime
import asyncio



class PDFService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraper = PDFScraper()
        self.transformer = DataTransformer()
        
    async def create_pdf_document(self, user_id: int, document_data: PDFDocumentCreate) -> PDFDocument:
        """Create a new PDF document record"""
        # Generate unique filename
        file_extension = os.path.splitext(document_data.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("uploads", unique_filename)
        
        db_document = PDFDocument(
            user_id=user_id,
            filename=unique_filename,
            original_filename=document_data.original_filename,
            file_path=file_path,
            file_size=document_data.file_size,
            source_type=document_data.source_type,
            source_url=document_data.source_url,
            status="pending"
        )
        
        self.db.add(db_document)
        await self.db.commit()
        await self.db.refresh(db_document)
        
        return db_document
    
    async def process_pdf(self, document_id: int, use_ocr: bool = False) -> PDFDocument:
        stmt = select(PDFDocument).where(PDFDocument.id == document_id)
        document = (await self.db.execute(stmt)).scalar_one_or_none()
        if not document:
            raise ValueError("Document not found")

        document.status = "processing"
        await self.db.commit()

        try:
            self.scraper.use_ocr = use_ocr
            extraction_result = self.scraper.extract_text_from_pdf(document.file_path)

            document.page_count = extraction_result["metadata"].get("page_count", 0)
            document.ocr_processed = use_ocr
            document.extraction_metadata = str(extraction_result["metadata"])

            try:
                ai_service = AIService()
                extracted_text = extraction_result.get("text", "")
                summary_text = ai_service.generate_summary(extracted_text)
                classification = ai_service.classify_report(extracted_text)
                entities = ai_service.extract_entities(extracted_text)

                self.db.add(AISummary(
                    pdf_document_id=document.id,
                    summary=summary_text,
                    classification=classification,
                    entities=entities
                ))

                insights_data = ai_service.generate_insights(extracted_text)
                self.db.add(Analytics(
                    pdf_document_id=document.id,
                    insights=insights_data.get("insights", []),
                    kpis=insights_data.get("kpis", {})
                ))
            except Exception as ai_err:
                print(f"[AI pipeline failed]: {ai_err}")

            document.status = "completed"

            if extraction_result["tables"]:
                structured_data = self.scraper.extract_tables_to_dataframe(extraction_result["tables"])
                if structured_data:
                    await self._create_dataset_from_data(
                        user_id=document.user_id,
                        pdf_document_id=document.id,
                        data=structured_data,
                        name=f"Dataset from {document.original_filename}"
                    )

            await self.db.commit()
            await self.db.refresh(document)
            return document

        except Exception as e:
            await self.db.rollback()
            document.status = "failed"
            document.error_message = str(e)
            await self.db.commit()
            raise e

    
    async def _create_dataset_from_data(self, user_id: int, pdf_document_id: int, data: List, name: str) -> Dataset:
        """Create dataset and data rows from extracted data"""
        # Transform data
        transformed_rows = self.transformer.transform_to_dataset_format(data, pdf_document_id)
        
        # Create dataset
        dataset = Dataset(
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            name=name,
            row_count=len(transformed_rows),
            status="ready"
        )
        
        self.db.add(dataset)
        await self.db.flush()
        
        # Add data rows
        for row_data in transformed_rows:
            data_row = DataRow(
                dataset_id=dataset.id,
                row_data=row_data["row_data"],
                extraction_method=row_data["extraction_method"],
                confidence_score=row_data["confidence_score"]
            )
            self.db.add(data_row)
        
        await self.db.commit()
        await self.db.refresh(dataset)
        
        return dataset
    
    async def get_user_documents(self, user_id: int, skip: int = 0, limit: int = 100) -> List[PDFDocument]:
        """Get all PDF documents for a user"""
        stmt = (
            select(PDFDocument)
            .where(PDFDocument.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return (await self.db.execute(stmt)).scalars().all()
    
    async def get_document(self, document_id: int, user_id: int) -> Optional[PDFDocument]:
        """Get a specific PDF document"""
        stmt = select(PDFDocument).where(
            PDFDocument.id == document_id,
            PDFDocument.user_id == user_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
    
    async def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a PDF document"""
        document = await self.get_document(document_id, user_id)
        if not document:
            return False
        
        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        await self.db.delete(document)
        await self.db.commit()
        
        return True
    
    async def scrape_pdf_from_url(self, user_id: int, url: str) -> PDFDocument:
        """Scrape PDF from URL"""
        # Create processing job
        job = ProcessingJob(
            user_id=user_id,
            job_type="scrape",
            status="running"
        )
        self.db.add(job)
        await self.db.commit()
        
        # Publish SSE event for job start
        asyncio.create_task(publish_job_event(
            user_id=user_id,
            job_data={
                "job_id": str(job.id),
                "status": "processing",
                "progress": 0,
                "filename": url
            }
        ))
        
        try:
            # Download PDF
            filename = url.split('/')[-1] or "scanned.pdf"
            unique_filename = f"{uuid.uuid4()}.pdf"
            file_path = os.path.join("uploads", unique_filename)
            
            self.scraper.download_pdf_from_url(url, file_path)
            
            # Publish progress update
            asyncio.create_task(publish_job_event(
                user_id=user_id,
                job_data={
                    "job_id": str(job.id),
                    "status": "processing",
                    "progress": 50,
                    "filename": filename
                }
            ))
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document record
            document_data = PDFDocumentCreate(
                filename=unique_filename,
                original_filename=filename,
                source_type="url",
                source_url=url,
                file_size=file_size
            )
            
            document = await self.create_pdf_document(user_id, document_data)
            
            # Update job
            job.status = "completed"
            job.pdf_document_id = document.id
            job.completed_at = datetime.utcnow()
            await self.db.commit()
            
            # Publish SSE event for completion
            asyncio.create_task(publish_job_event(
                user_id=user_id,
                job_data={
                    "job_id": str(job.id),
                    "status": "done",
                    "progress": 100,
                    "filename": filename
                }
            ))
            
            return document
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self.db.commit()
            
            # Publish SSE event for failure
            asyncio.create_task(publish_job_event(
                user_id=user_id,
                job_data={
                    "job_id": str(job.id),
                    "status": "failed",
                    "progress": 0,
                    "filename": url
                }
            ))
            
            raise e
