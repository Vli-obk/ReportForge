import logging
import traceback
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.api.deps import get_current_user
from app.api.v1 import auth, pdfs, datasets, pipeline, gemini, financial_reports
from app.database.session import get_db
from app.models.user import User

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)
logger = logging.getLogger(__name__)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "request_failed",
            extra={
                "request_id": request_id,
                "endpoint": f"{request.method} {request.url.path}",
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            },
        )
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error", "request_id": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    return response

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
app.include_router(gemini.router, prefix=f"{settings.API_V1_STR}/gemini", tags=["gemini"])
app.include_router(
    financial_reports.router,
    prefix=f"{settings.API_V1_STR}/financial-reports",
    tags=["financial-reports"],
)


@app.get(f"{settings.API_V1_STR}/dashboard/statistics")
async def dashboard_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.api.v1.pdfs import get_statistics

    return await get_statistics(current_user=current_user, db=db)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": "Invalid request", "details": exc.errors()},
    )


@app.get("/")
def root():
    return {
        "message": "ReportForge API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "online",
    }


@app.get(f"{settings.API_V1_STR}/overview")
def api_overview():
    return root()


@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "reachable"}


@app.get(f"{settings.API_V1_STR}/health")
def api_health_check():
    return health_check()
