import asyncio
import logging
import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.gemini import (
    GeminiErrorResponse,
    GeminiExtractRequest,
    GeminiExtractResponse,
    GeminiStructuredExtractRequest,
    GeminiStructuredExtractResponse,
)
from app.services.gemini_service import GeminiService, ModelNotFoundError, GeminiTimeoutError, GeminiUnavailableError, GeminiRateLimitError


router = APIRouter()
logger = logging.getLogger(__name__)


def error_response(status_code: int, error: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": error})


def get_gemini_service() -> GeminiService:
    return GeminiService()


@router.get("/health")
async def gemini_health():
    try:
        gemini = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        result = await gemini.async_health_check()
        available = result["available"] and result["model_available"]
        response = {
            "status": "online" if available else "offline",
            "model": settings.GEMINI_MODEL,
            "available": available,
        }
        if result.get("error"):
            response["error"] = result["error"]
        return response
    except Exception as e:
        return {
            "status": "offline",
            "model": settings.GEMINI_MODEL,
            "available": False,
            "error": str(e),
        }


@router.post(
    "/extract",
    response_model=GeminiExtractResponse,
    responses={
        400: {"model": GeminiErrorResponse},
        404: {"model": GeminiErrorResponse},
        503: {"model": GeminiErrorResponse},
        504: {"model": GeminiErrorResponse},
    },
)
async def extract(
    payload: GeminiExtractRequest,
    current_user: User = Depends(get_current_user),
    service: GeminiService = Depends(get_gemini_service),
):
    started = time.perf_counter()
    logger.info("gemini_extract_start", extra={"user_id": current_user.id, "model": service.model})
    try:
        response = await service.extract_from_text(payload.text, payload.temperature, payload.max_tokens)
        processing_time = round(time.perf_counter() - started, 3)
        logger.info(
            "gemini_extract_complete",
            extra={"user_id": current_user.id, "model": service.model, "processing_time": processing_time},
        )
        return {"success": True, "model": service.model, "response": response, "processing_time": processing_time}
    except GeminiRateLimitError as exc:
        return error_response(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    except ModelNotFoundError as exc:
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except GeminiTimeoutError:
        return error_response(status.HTTP_504_GATEWAY_TIMEOUT, "Gemini request timeout")
    except GeminiUnavailableError as exc:
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, str(exc))


@router.post(
    "/extract_structured",
    response_model=GeminiStructuredExtractResponse,
    responses={
        400: {"model": GeminiErrorResponse},
        404: {"model": GeminiErrorResponse},
        503: {"model": GeminiErrorResponse},
        504: {"model": GeminiErrorResponse},
    },
)
async def extract_structured(
    payload: GeminiStructuredExtractRequest,
    current_user: User = Depends(get_current_user),
    service: GeminiService = Depends(get_gemini_service),
):
    started = time.perf_counter()
    logger.info(
        "gemini_structured_extract_start",
        extra={"user_id": current_user.id, "model": service.model},
    )
    try:
        data = await asyncio.to_thread(
            service.extract_structured_data,
            payload.text,
            payload.max_tokens,
            payload.temperature,
        )
        processing_time = round(time.perf_counter() - started, 3)
        logger.info(
            "gemini_structured_extract_complete",
            extra={"user_id": current_user.id, "model": service.model, "processing_time": processing_time},
        )
        return {
            "success": True,
            "model": service.model,
            "data": data,
            "processing_time": processing_time,
        }
    except GeminiRateLimitError as exc:
        return error_response(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    except ModelNotFoundError as exc:
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except GeminiTimeoutError:
        return error_response(status.HTTP_504_GATEWAY_TIMEOUT, "Gemini request timeout")
    except GeminiUnavailableError as exc:
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception as exc:
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
