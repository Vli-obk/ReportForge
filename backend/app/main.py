from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, pdfs, datasets, pipeline

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(pdfs.router, prefix=f"{settings.API_V1_STR}/pdfs", tags=["pdfs"])
app.include_router(datasets.router, prefix=f"{settings.API_V1_STR}/datasets", tags=["datasets"])
app.include_router(pipeline.router, prefix=f"{settings.API_V1_STR}/pipeline", tags=["pipeline"])


@app.get("/")
def root():
    return {
        "message": "PDF Analytics Platform API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
