"""ElevenLabs STT route tests (Phase 4)."""

from __future__ import annotations


def _auth_header(client, email="stt@test.com"):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "pass123",
            "full_name": "Speaker",
            "role": "veteran",
        },
    )
    login = client.post("/auth/login", json={"email": email, "password": "pass123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_stt_success_returns_transcript(client, monkeypatch):
    from app.routers import stt

    async def fake_convert(filename, content, content_type):
        assert filename == "clip.webm"
        assert content == b"abc123"
        assert content_type == "audio/webm"
        return "transcribed text"

    monkeypatch.setattr(stt.settings, "elevenlabs_api_key", "test-key")
    monkeypatch.setattr(stt, "_convert_with_elevenlabs", fake_convert)

    headers = _auth_header(client)
    response = client.post(
        "/stt/elevenlabs",
        headers=headers,
        files={"audio": ("clip.webm", b"abc123", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"transcript": "transcribed text"}


def test_stt_rejects_unsupported_file_type(client, monkeypatch):
    from app.routers import stt

    monkeypatch.setattr(stt.settings, "elevenlabs_api_key", "test-key")

    headers = _auth_header(client, email="stt-type@test.com")
    response = client.post(
        "/stt/elevenlabs",
        headers=headers,
        files={"audio": ("note.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_stt_rejects_oversized_file(client, monkeypatch):
    from app.routers import stt

    monkeypatch.setattr(stt.settings, "elevenlabs_api_key", "test-key")
    monkeypatch.setattr(stt, "MAX_AUDIO_BYTES", 4)

    headers = _auth_header(client, email="stt-size@test.com")
    response = client.post(
        "/stt/elevenlabs",
        headers=headers,
        files={"audio": ("clip.webm", b"12345", "audio/webm")},
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_stt_requires_api_key(client, monkeypatch):
    from app.routers import stt

    monkeypatch.setattr(stt.settings, "elevenlabs_api_key", "")

    headers = _auth_header(client, email="stt-key@test.com")
    response = client.post(
        "/stt/elevenlabs",
        headers=headers,
        files={"audio": ("clip.webm", b"abc", "audio/webm")},
    )

    assert response.status_code == 503
    assert "ELEVENLABS_API_KEY" in response.json()["detail"]
