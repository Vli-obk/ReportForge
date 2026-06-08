import asyncio

# Shared semaphore that serializes all on-demand pdfplumber extractions across
# both the API endpoints (pdfs.py) and the background processing pipeline
# (pdf_service.py).  Each extraction peaks at ~235 MB; allowing two concurrent
# ones risks an OOM kill under Docker Desktop's default memory limits.
pdf_extract_semaphore = asyncio.Semaphore(1)
