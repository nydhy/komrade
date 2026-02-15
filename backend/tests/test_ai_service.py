"""AI service + AI test router tests (Phase 1)."""

import pytest

from app.services import ai_service
from app.services.ai_service import AIServiceError, generate_structured


TEST_SCHEMA = {
    "type": "object",
    "required": ["summary", "confidence"],
    "properties": {
        "summary": {"type": "string"},
        "confidence": {"type": "number"},
    },
}


def test_generate_structured_retries_after_invalid_json(monkeypatch):
    """Invalid JSON on first attempt should trigger one retry and then succeed."""
    calls: list[str] = []

    def fake_call_provider(provider, prompt, schema):
        calls.append(prompt)
        if len(calls) == 1:
            return "not-json"
        return '{"summary":"ok","confidence":0.91}'

    monkeypatch.setattr(ai_service, "_call_provider", fake_call_provider)

    out = generate_structured(
        provider="gemini",
        task="test task",
        payload={"text": "hello"},
        schema=TEST_SCHEMA,
    )

    assert out == {"summary": "ok", "confidence": 0.91}
    assert len(calls) == 2
    assert "previous output was invalid" in calls[1].lower()


def test_generate_structured_retries_after_schema_mismatch(monkeypatch):
    """Schema mismatch on first attempt should retry with correction instruction."""
    calls = {"count": 0}

    def fake_call_provider(provider, prompt, schema):
        calls["count"] += 1
        if calls["count"] == 1:
            return '{"summary":"missing confidence"}'
        return '{"summary":"fixed","confidence":0.5}'

    monkeypatch.setattr(ai_service, "_call_provider", fake_call_provider)

    out = generate_structured(
        provider="ollama",
        task="test task",
        payload={"topic": "test"},
        schema=TEST_SCHEMA,
    )

    assert out["summary"] == "fixed"
    assert out["confidence"] == 0.5
    assert calls["count"] == 2


def test_generate_structured_raises_after_retry_exhausted(monkeypatch):
    """Two invalid attempts should raise AIServiceError."""

    def fake_call_provider(provider, prompt, schema):
        return "still-not-json"

    monkeypatch.setattr(ai_service, "_call_provider", fake_call_provider)

    with pytest.raises(AIServiceError) as exc:
        generate_structured(
            provider="gemini",
            task="test task",
            payload={"x": 1},
            schema=TEST_SCHEMA,
        )

    assert "failed to return valid structured json" in str(exc.value).lower()


def test_ai_test_router_returns_422_when_service_fails(client, monkeypatch):
    """Router should map AI service errors to HTTP 422."""
    from app.routers import ai_test

    def fake_generate_structured(provider, task, payload, schema):
        raise AIServiceError("schema mismatch from provider")

    monkeypatch.setattr(ai_test, "generate_structured", fake_generate_structured)

    response = client.post(
        "/ai/test-structured",
        json={"provider": "gemini", "payload": {"text": "hello"}},
    )

    assert response.status_code == 422
    assert "schema mismatch" in response.json()["detail"]
