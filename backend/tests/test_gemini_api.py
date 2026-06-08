from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.v1 import gemini as gemini_router


class FakeService:
    model = "llama3"

    async def extract_from_text(self, text, temperature=0.3, max_tokens=1000):
        return "insights"

    async def async_health_check(self):
        return {"available": True, "model_available": True, "model": self.model, "error": None}


def override_user():
    return SimpleNamespace(id=1)


def override_service():
    return FakeService()


def client():
    test_app = FastAPI()

    @test_app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(status_code=422, content={"success": False, "error": "Invalid request", "details": exc.errors()})

    test_app.include_router(gemini_router.router, prefix="/api/v1/gemini")
    test_app.dependency_overrides[gemini_router.get_current_user] = override_user
    test_app.dependency_overrides[gemini_router.get_gemini_service] = override_service
    return TestClient(test_app)


def test_extract_authenticated_success():
    response = client().post("/api/v1/gemini/extract", json={"text": "pdf text", "temperature": 0.3, "max_tokens": 100})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["model"] == "llama3"


def test_extract_invalid_payload():
    response = client().post("/api/v1/gemini/extract", json={"text": "", "temperature": 0.3, "max_tokens": 100})
    assert response.status_code == 422


def test_extract_unauthenticated():
    test_app = FastAPI()
    test_app.include_router(gemini_router.router, prefix="/api/v1/gemini")
    response = TestClient(test_app).post("/api/v1/gemini/extract", json={"text": "pdf text"})
    assert response.status_code in (401, 403)


def test_health_authenticated():
    response = client().get("/api/v1/gemini/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
