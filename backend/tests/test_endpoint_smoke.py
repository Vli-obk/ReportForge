import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.session import Base, get_db
from app.main import app as fastapi_app
from app.models.pdf_document import PDFDocument
from app.models.user import User
from app.services.pdf_service import PDFService
import app.models.ai_summary
import app.models.analytics
import app.models.data_row
import app.models.dataset
import app.models.pdf_document
import app.models.processing_job
import app.models.user


test_engine = create_async_engine("sqlite+aiosqlite:///C:/tmp/pdf_analytics_endpoint_smoke.db")
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


def _init_db() -> None:
    async def init() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())


def _pdf_bytes(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = b"%PDF-1.4\n"
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_at = len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets
    )
    trailer = f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    return body + xref + trailer


def test_core_endpoints_do_not_500():
    _init_db()
    fastapi_app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(fastapi_app)
    email = f"smoke_{uuid.uuid4().hex[:8]}@test.com"

    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Smoke Test", "password": "pass12345"},
    )
    assert register.status_code == 200

    login = client.post("/api/v1/auth/login", data={"username": email, "password": "pass12345"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    expected = {
        "/": 200,
        "/health": 200,
        "/api/v1/health": 200,
        "/api/v1/auth/me": 200,
        "/api/v1/overview": 200,
        "/api/v1/pdfs": 200,
        "/api/v1/pdfs/999": 404,
        "/api/v1/pdfs/statistics/overview": 200,
        "/api/v1/datasets": 200,
        "/api/v1/datasets/999": 404,
        "/api/v1/pipeline/jobs/999": 404,
        "/api/v1/pipeline/health": 200,
        "/api/v1/gemini/health": 200,
    }
    for path, status_code in expected.items():
        response = client.get(path, headers=headers if path.startswith("/api") else {})
        assert response.status_code == status_code, path

    response = client.post("/api/v1/gemini/extract", headers=headers, json={"text": "sample extracted PDF text"})
    assert response.status_code in {200, 404, 503, 504}
    fastapi_app.dependency_overrides.clear()


def test_pdf_processing_pipeline_survives_gemini_unavailable(tmp_path):
    _init_db()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(_pdf_bytes("Sales Report 2026 Revenue 1000"))

    async def run_pipeline() -> str:
        async with TestSessionLocal() as session:
            user = User(email="pipeline@test.com", full_name="Pipeline Test", hashed_password="x")
            session.add(user)
            await session.flush()
            document = PDFDocument(
                user_id=user.id,
                filename="sample.pdf",
                original_filename="sample.pdf",
                file_path=str(pdf_path),
                file_size=pdf_path.stat().st_size,
                status="pending",
            )
            session.add(document)
            await session.commit()
            await session.refresh(document)

            service = PDFService(session)
            processed = await service.process_pdf(document.id)
            return processed.status

    assert asyncio.run(run_pipeline()) == "completed"
