from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List
from app.database.session import get_db
from app.schemas.pdf_document import PDFDocument, PDFUploadResponse
from app.schemas.processing_job import Statistics
from app.schemas.ai_summary import AISummary as AISummarySchema
from app.schemas.analytics import Analytics as AnalyticsSchema
from app.models.pdf_document import PDFDocument as PDFDocumentModel
from app.models.ai_summary import AISummary as AISummaryModel
from app.models.analytics import Analytics as AnalyticsModel
from app.models.user import User
from app.api.deps import get_current_user
from app.services.pdf_service import PDFService
import os
import shutil


router = APIRouter()


@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    use_ocr: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a PDF file"""
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    
    # Create document record
    from app.schemas.pdf_document import PDFDocumentCreate
    document_data = PDFDocumentCreate(
        filename=file.filename,
        original_filename=file.filename,
        file_size=file_size,
        source_type="upload"
    )
    
    document = PDFDocumentModel(
        user_id=current_user.id,
        filename=document_data.filename,
        original_filename=document_data.original_filename,
        file_path=file_path,
        file_size=document_data.file_size,
        source_type=document_data.source_type,
        source_url=document_data.source_url,
        status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    pdf_service = PDFService(db)
    await pdf_service.process_pdf(document.id, use_ocr=use_ocr)
    
    return PDFUploadResponse(
        document_id=document.id,
        filename=document.original_filename,
        status=document.status,
        message="PDF uploaded successfully"
    )


@router.post("/scrape", response_model=PDFUploadResponse)
async def scrape_pdf(
    url: str = Form(...),
    use_ocr: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Scrape PDF from URL"""
    pdf_service = PDFService(db)
    
    try:
        document = await pdf_service.scrape_pdf_from_url(current_user.id, url)
        
        # Process PDF
        try:
            await pdf_service.process_pdf(document.id, use_ocr=use_ocr)
        except Exception as e:
            pass
        
        return PDFUploadResponse(
            document_id=document.id,
            filename=document.original_filename,
            status=document.status,
            message="PDF scraped successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[PDFDocument])
async def get_pdfs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all PDFs for current user"""
    pdf_service = PDFService(db)
    return await pdf_service.get_user_documents(current_user.id, skip, limit)


@router.get("/{document_id}", response_model=PDFDocument)
async def get_pdf(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific PDF"""
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.delete("/{document_id}")
async def delete_pdf(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a PDF"""
    pdf_service = PDFService(db)
    success = await pdf_service.delete_document(document_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {"message": "Document deleted successfully"}


@router.get("/statistics/overview", response_model=Statistics)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics"""
    from app.models.dataset import Dataset
    from app.models.data_row import DataRow
    from app.models.processing_job import ProcessingJob

    total_pdfs = (await db.execute(
        select(func.count()).select_from(PDFDocumentModel).where(PDFDocumentModel.user_id == current_user.id)
    )).scalar()
    total_rows = (await db.execute(
        select(func.count()).select_from(DataRow).join(Dataset).where(Dataset.user_id == current_user.id)
    )).scalar()
    ocr_processed = (await db.execute(
        select(func.count()).select_from(PDFDocumentModel).where(
            PDFDocumentModel.user_id == current_user.id,
            PDFDocumentModel.ocr_processed == True
        )
    )).scalar()
    failed_jobs = (await db.execute(
        select(func.count()).select_from(ProcessingJob).where(
            ProcessingJob.user_id == current_user.id,
            ProcessingJob.status == "failed"
        )
    )).scalar()
    storage = (await db.execute(
        select(func.sum(PDFDocumentModel.file_size)).where(PDFDocumentModel.user_id == current_user.id)
    )).scalar() or 0

    return Statistics(
        total_pdfs=total_pdfs,
        total_rows=total_rows,
        ocr_processed=ocr_processed,
        failed_jobs=failed_jobs,
        storage_used=storage
    )


@router.get("/{document_id}/ai-summary", response_model=AISummarySchema)
async def get_pdf_ai_summary(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI summary, classification and key entities for a PDF"""
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    summary = db.query(AISummaryModel).filter(AISummaryModel.pdf_document_id == document_id).first()
    if not summary:
        # If the document is completed but has no summary, run quick on-demand AI extraction
        if document.status == "completed":
            try:
                from app.scraper.pdf_scraper import PDFScraper
                from app.services.ai_service import AIService
                scraper = PDFScraper()
                ai_service = AIService()
                extraction_result = scraper.extract_text_from_pdf(document.file_path)
                extracted_text = extraction_result.get("text", "")
                
                summary_text = ai_service.generate_summary(extracted_text)
                classification = ai_service.classify_report(extracted_text)
                entities = ai_service.extract_entities(extracted_text)
                
                summary = AISummaryModel(
                    pdf_document_id=document.id,
                    summary=summary_text,
                    classification=classification,
                    entities=entities
                )
                db.add(summary)
                db.commit()
                db.refresh(summary)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate summary on demand: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document status is '{document.status}' and AI summary is unavailable."
            )
            
    return summary


@router.get("/{document_id}/analytics", response_model=AnalyticsSchema)
async def get_pdf_analytics(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI insights and KPIs for a PDF"""
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    analytics = db.query(AnalyticsModel).filter(AnalyticsModel.pdf_document_id == document_id).first()
    if not analytics:
        if document.status == "completed":
            try:
                from app.scraper.pdf_scraper import PDFScraper
                from app.services.ai_service import AIService
                scraper = PDFScraper()
                ai_service = AIService()
                extraction_result = scraper.extract_text_from_pdf(document.file_path)
                extracted_text = extraction_result.get("text", "")
                
                insights_data = ai_service.generate_insights(extracted_text)
                
                analytics = AnalyticsModel(
                    pdf_document_id=document.id,
                    insights=insights_data.get("insights", []),
                    kpis=insights_data.get("kpis", {})
                )
                db.add(analytics)
                db.commit()
                db.refresh(analytics)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate analytics on demand: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document status is '{document.status}' and AI analytics is unavailable."
            )
            
    return analytics


@router.post("/{document_id}/trigger-ai", response_model=AISummarySchema)
async def trigger_pdf_ai(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Force re-run AI generation for a PDF"""
    pdf_service = PDFService(db)
    document = await pdf_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document status must be completed to run AI. Current: {document.status}"
        )
        
    try:
        from app.scraper.pdf_scraper import PDFScraper
        from app.services.ai_service import AIService
        scraper = PDFScraper()
        ai_service = AIService()
        extraction_result = scraper.extract_text_from_pdf(document.file_path)
        extracted_text = extraction_result.get("text", "")
        
        # Re-generate summary
        summary_text = ai_service.generate_summary(extracted_text)
        classification = ai_service.classify_report(extracted_text)
        entities = ai_service.extract_entities(extracted_text)
        
        # Update or create AISummary
        summary = db.query(AISummaryModel).filter(AISummaryModel.pdf_document_id == document_id).first()
        if summary:
            summary.summary = summary_text
            summary.classification = classification
            summary.entities = entities
        else:
            summary = AISummaryModel(
                pdf_document_id=document.id,
                summary=summary_text,
                classification=classification,
                entities=entities
            )
            db.add(summary)
            
        # Re-generate Analytics
        insights_data = ai_service.generate_insights(extracted_text)
        analytics = db.query(AnalyticsModel).filter(AnalyticsModel.pdf_document_id == document_id).first()
        if analytics:
            analytics.insights = insights_data.get("insights", [])
            analytics.kpis = insights_data.get("kpis", {})
        else:
            analytics = AnalyticsModel(
                pdf_document_id=document.id,
                insights=insights_data.get("insights", []),
                kpis=insights_data.get("kpis", {})
            )
            db.add(analytics)
            
        db.commit()
        db.refresh(summary)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-run AI generation: {str(e)}"
        )

