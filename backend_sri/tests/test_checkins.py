"""Mood check-ins API tests."""


def test_mood_score_validation(client):
    """mood_score must be 1-5."""
    client.post(
        "/auth/register",
        json={"email": "v@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    token = client.post("/auth/login", json={"email": "v@test.com", "password": "pass"}).json()["access_token"]

    # Valid
    r = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"mood_score": 3, "tags": [], "wants_company": False},
    )
    assert r.status_code == 200

    # Invalid: 0
    r = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"mood_score": 0, "tags": [], "wants_company": False},
    )
    assert r.status_code == 422

    # Invalid: 6
    r = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"mood_score": 6, "tags": [], "wants_company": False},
    )
    assert r.status_code == 422


def test_only_veteran_can_create(client):
    """Only veteran can create check-in."""
    client.post(
        "/auth/register",
        json={"email": "buddy_chk@test.com", "password": "pass", "full_name": "B", "role": "buddy"},
    )
    token = client.post("/auth/login", json={"email": "buddy_chk@test.com", "password": "pass"}).json()["access_token"]

    r = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"mood_score": 3, "tags": [], "wants_company": False},
    )
    assert r.status_code == 403


def test_fetch_returns_sorted_newest_first(client):
    """GET /checkins/me returns check-ins sorted newest first."""
    client.post(
        "/auth/register",
        json={"email": "v_sort@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    token = client.post("/auth/login", json={"email": "v_sort@test.com", "password": "pass"}).json()["access_token"]

    # Create 3 check-ins
    for i in range(3):
        client.post(
            "/checkins",
            headers={"Authorization": f"Bearer {token}"},
            json={"mood_score": i + 1, "tags": [f"tag{i}"], "wants_company": False},
        )

    r = client.get("/checkins/me?limit=30", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
    # Newest first: last created has tag2, then tag1, then tag0
    assert items[0]["tags"] == ["tag2"]
    assert items[1]["tags"] == ["tag1"]
    assert items[2]["tags"] == ["tag0"]


def test_can_create_checkin(client):
    """Can create check-in with full payload."""
    client.post(
        "/auth/register",
        json={"email": "v@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    token = client.post("/auth/login", json={"email": "v@test.com", "password": "pass"}).json()["access_token"]

    r = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mood_score": 4,
            "tags": ["calm", "hopeful"],
            "note": "Feeling better today",
            "wants_company": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mood_score"] == 4
    assert data["tags"] == ["calm", "hopeful"]
    assert data["note"] == "Feeling better today"
    assert data["wants_company"] is True
    assert "id" in data
    assert "created_at" in data


def test_fetch_last_30(client):
    """GET /checkins/me?limit=30 returns up to 30 items."""
    client.post(
        "/auth/register",
        json={"email": "v_limit@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    token = client.post("/auth/login", json={"email": "v_limit@test.com", "password": "pass"}).json()["access_token"]

    # Create 5 check-ins
    for _ in range(5):
        client.post(
            "/checkins",
            headers={"Authorization": f"Bearer {token}"},
            json={"mood_score": 3, "tags": [], "wants_company": False},
        )

    r = client.get("/checkins/me?limit=30", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 5
