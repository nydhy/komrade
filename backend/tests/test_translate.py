"""Translation Layer endpoint tests (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda d: d.get(key), reverse=reverse)
        return self

    def limit(self, limit):
        self._docs = self._docs[:limit]
        return self

    async def to_list(self, length):
        return self._docs[:length]


class _FakeCollection:
    def __init__(self):
        self.inserted = []
        self.seed = []

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return {"inserted_id": "fake"}

    def find(self, query):
        user_id = query.get("user_id")
        docs = [d.copy() for d in self.seed if d.get("user_id") == user_id]
        return _FakeCursor(docs)


def _auth_header(client, email="translate@test.com"):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "pass123",
            "full_name": "Translator",
            "role": "veteran",
        },
    )
    login = client.post("/auth/login", json={"email": email, "password": "pass123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_translate_calls_ai_and_inserts_doc(client, monkeypatch):
    from app.routers import translate

    fake_collection = _FakeCollection()

    def fake_generate_structured(provider, task, payload, schema):
        return {
            "empathetic_personalized_answer": "Personalized empathetic answer",
            "safety_flag": "normal",
        }

    monkeypatch.setattr(translate, "generate_structured", fake_generate_structured)
    monkeypatch.setattr(translate, "get_translations_collection", lambda: fake_collection)
    monkeypatch.setattr(translate.settings, "ai_provider", "ollama")

    headers = _auth_header(client)
    response = client.post(
        "/translate",
        headers=headers,
        json={
            "message": "Can you rewrite this kindly?",
            "context": {"tone": "supportive"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["empathetic_personalized_answer"] == "Personalized empathetic answer"
    assert body["safety_flag"] == "normal"

    assert len(fake_collection.inserted) == 1
    saved = fake_collection.inserted[0]
    assert saved["provider"] == "ollama"
    assert saved["question"] == "Can you rewrite this kindly?"
    assert saved["response"] == "Personalized empathetic answer"
    assert saved["context"] == {"tone": "supportive"}
    assert saved["safety_flag"] == "normal"


def test_translate_crisis_fallback_and_insert(client, monkeypatch):
    from app.routers import translate

    fake_collection = _FakeCollection()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("AI service should not be called for crisis fallback")

    monkeypatch.setattr(translate, "generate_structured", fail_if_called)
    monkeypatch.setattr(translate, "get_translations_collection", lambda: fake_collection)
    monkeypatch.setattr(translate.settings, "ai_provider", "ollama")

    headers = _auth_header(client, email="crisis@test.com")
    response = client.post(
        "/translate",
        headers=headers,
        json={
            "message": "I want to kill myself",
            "context": {"source": "chat"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["safety_flag"] == "crisis"
    assert "988" in body["empathetic_personalized_answer"]

    assert len(fake_collection.inserted) == 1
    assert fake_collection.inserted[0]["safety_flag"] == "crisis"


def test_translate_history_returns_newest_first(client, monkeypatch):
    from app.routers import translate

    fake_collection = _FakeCollection()
    monkeypatch.setattr(translate, "get_translations_collection", lambda: fake_collection)

    headers = _auth_header(client, email="history@test.com")
    me = client.get("/auth/me", headers=headers).json()
    my_user_id = me["id"]

    now = datetime.now(timezone.utc)
    fake_collection.seed = [
        {
            "_id": "1",
            "created_at": now - timedelta(minutes=10),
            "user_id": my_user_id,
            "provider": "ollama",
            "question": "old",
            "response": "old-e",
            "context": None,
            "empathetic_personalized_answer": "old-e",
            "safety_flag": "normal",
        },
        {
            "_id": "2",
            "created_at": now,
            "user_id": my_user_id,
            "provider": "ollama",
            "question": "new",
            "response": "new-e",
            "context": None,
            "empathetic_personalized_answer": "new-e",
            "safety_flag": "normal",
        },
        {
            "_id": "3",
            "created_at": now + timedelta(minutes=1),
            "user_id": 9999,
            "provider": "ollama",
            "question": "other-user",
            "response": "y",
            "context": None,
            "empathetic_personalized_answer": "y",
            "safety_flag": "normal",
        },
    ]

    response = client.get("/translate/history?limit=10", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["question"] == "new"
    assert body[0]["response"] == "new-e"
    assert body[1]["question"] == "old"
    assert body[1]["response"] == "old-e"
    assert all(item["user_id"] == my_user_id for item in body)
