import asyncio

import pytest
import requests

from app.services.gemini_service import ModelNotFoundError, GeminiService, GeminiTimeoutError, GeminiUnavailableError


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_generate_success(monkeypatch):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url))
        if url.endswith("/api/tags"):
            return FakeResponse(payload={"models": [{"name": "llama3:latest"}]})
        return FakeResponse(payload={"response": "ok"})

    monkeypatch.setattr(requests, "request", fake_request)
    service = GeminiService(model="llama3", api_key="test")
    assert asyncio.run(service.generate("hello")) == "ok"
    assert calls[0][1].endswith("/v1beta/models/llama3")
    assert calls[-1][1].endswith("/v1beta/models/llama3:generateContent")


def test_generate_content_response(monkeypatch):
    def fake_request(method, url, **kwargs):
        if method == "GET":
            return FakeResponse(payload={"name": "models/gemini-1.5-pro"})
        return FakeResponse(payload={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    monkeypatch.setattr(requests, "request", fake_request)
    service = GeminiService(model="gemini-1.5-pro", api_key="test")
    assert asyncio.run(service.generate("hello")) == "ok"


def test_structured_json_cleanup():
    service = GeminiService(api_key="test")
    data = service._parse_json_response('```json\n[{"Amount":"$1,200.50","Rate":"5%","Missing":"","Loss":"(10)"}]\n```')
    assert data == [{"Amount": 1200.50, "Rate": 5.0, "Missing": None, "Loss": -10.0}]


def test_timeout(monkeypatch):
    def fake_request(method, url, **kwargs):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(requests, "request", fake_request)
    service = GeminiService(retries=0, api_key="test")
    with pytest.raises(GeminiTimeoutError):
        service.check_connection()


def test_invalid_model(monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *a, **k: FakeResponse(payload={"name": "mistral"}, status_code=404))
    service = GeminiService(model="llama3", api_key="test")
    with pytest.raises(ModelNotFoundError):
        service.check_connection()


def test_connection_failure(monkeypatch):
    def fake_request(method, url, **kwargs):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(requests, "request", fake_request)
    service = GeminiService(retries=0, api_key="test")
    with pytest.raises(GeminiUnavailableError):
        service.check_connection()


def test_invalid_response(monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *a, **k: FakeResponse(payload=ValueError("bad json")))
    service = GeminiService(api_key="test")
    with pytest.raises(GeminiUnavailableError):
        service.check_connection()


def test_empty_prompt():
    service = GeminiService(api_key="test")
    with pytest.raises(ValueError):
        asyncio.run(service.generate(" "))
