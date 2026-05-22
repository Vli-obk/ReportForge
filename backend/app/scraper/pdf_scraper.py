import pdfplumber
import pytesseract
from PIL import Image
import io
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path
import os


class PDFScraper:
    def __init__(self, use_ocr: bool = False):
        self.use_ocr = use_ocr
        
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and metadata from PDF file"""
        result = {
            "text": "",
            "pages": [],
            "metadata": {},
            "tables": []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["metadata"]["page_count"] = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages):
                    page_data = {
                        "page_number": i + 1,
                        "text": page.extract_text() or "",
                        "tables": []
                    }
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            page_data["tables"].append(table)
                            result["tables"].append({
                                "page": i + 1,
                                "data": table
                            })
                    
                    # If no text found and OCR is enabled, try OCR
                    if not page_data["text"].strip() and self.use_ocr:
                        ocr_text = self._extract_ocr_from_page(page)
                        page_data["text"] = ocr_text
                        page_data["extraction_method"] = "ocr"
                    else:
                        page_data["extraction_method"] = "pdfplumber"
                    
                    result["pages"].append(page_data)
                    result["text"] += page_data["text"] + "\n\n"
                    
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
            
        return result
    
    def _extract_ocr_from_page(self, page) -> str:
        """Extract text from page using OCR"""
        try:
            # Convert page to image
            img = page.to_image()
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Use pytesseract
            pil_image = Image.open(img_bytes)
            text = pytesseract.image_to_string(pil_image)
            return text
        except Exception as e:
            print(f"OCR extraction failed: {str(e)}")
            return ""
    
    def download_pdf_from_url(self, url: str, save_path: str) -> str:
        """Download PDF from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Verify it's a PDF
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' not in content_type:
                raise Exception("URL does not point to a PDF file")
            
            # Save file
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return save_path
            
        except Exception as e:
            raise Exception(f"Failed to download PDF: {str(e)}")
    
    def extract_tables_to_dataframe(self, tables: List[List]) -> List[Dict[str, Any]]:
        """Convert extracted tables to structured data"""
        structured_data = []
        
        for table_info in tables:
            table_data = table_info["data"]
            if not table_data:
                continue
                
            # Assume first row is header
            headers = table_data[0]
            rows = table_data[1:]
            
            for row in rows:
                if len(row) == len(headers):
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if header:
                            row_dict[str(header)] = row[i] if i < len(row) else None
                    if row_dict:
                        structured_data.append(row_dict)
                        
        return structured_data
