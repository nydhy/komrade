"""Module 9 — Settings, quiet hours, reports, block tests."""


def _register_and_login(client, email, role="buddy"):
    client.post(
        "/auth/register",
        json={"email": email, "password": "pass", "full_name": "Test", "role": role},
    )
    return client.post("/auth/login", json={"email": email, "password": "pass"}).json()["access_token"]


def test_get_default_settings(client):
    """GET /settings/me returns defaults for new user."""
    tok = _register_and_login(client, "set1@test.com")
    r = client.get("/settings/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert data["quiet_hours_start"] is None
    assert data["quiet_hours_end"] is None
    assert data["share_precise_location"] is True


def test_update_settings(client):
    """PUT /settings/me updates quiet hours and privacy."""
    tok = _register_and_login(client, "set2@test.com")
    r = client.put(
        "/settings/me",
        headers={"Authorization": f"Bearer {tok}"},
        json={"quiet_hours_start": "22:00", "quiet_hours_end": "07:00", "share_precise_location": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["quiet_hours_start"] == "22:00"
    assert data["quiet_hours_end"] == "07:00"
    assert data["share_precise_location"] is False


def test_invalid_time_format(client):
    """Invalid HH:MM format is rejected."""
    tok = _register_and_login(client, "set3@test.com")
    r = client.put(
        "/settings/me",
        headers={"Authorization": f"Bearer {tok}"},
        json={"quiet_hours_start": "25:00"},
    )
    assert r.status_code == 422


def test_report_user(client):
    """Can report another user."""
    tok1 = _register_and_login(client, "reporter@test.com")
    _register_and_login(client, "reported@test.com")
    # Need to find reported user's id
    me = client.post("/auth/login", json={"email": "reported@test.com", "password": "pass"}).json()
    # Register returns id in a separate call - get from /auth/me
    tok2 = me["access_token"]
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tok2}"}).json()
    reported_id = me_resp["id"]

    r = client.post(
        "/report",
        headers={"Authorization": f"Bearer {tok1}"},
        json={"reported_user_id": reported_id, "reason": "Inappropriate behavior in messages"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "reported"


def test_cannot_report_self(client):
    """Cannot report yourself."""
    tok = _register_and_login(client, "selfreport@test.com")
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    r = client.post(
        "/report",
        headers={"Authorization": f"Bearer {tok}"},
        json={"reported_user_id": me["id"], "reason": "This should fail because self"},
    )
    assert r.status_code == 400


def test_block_buddy_link(client):
    """Can block a buddy link."""
    v_tok = _register_and_login(client, "v_block@test.com", role="veteran")
    _register_and_login(client, "b_block@test.com", role="buddy")

    # Invite + accept
    client.post(
        "/buddies/invite",
        headers={"Authorization": f"Bearer {v_tok}"},
        json={"buddy_email": "b_block@test.com"},
    )
    b_tok = client.post("/auth/login", json={"email": "b_block@test.com", "password": "pass"}).json()["access_token"]
    invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_tok}"}).json()
    link_id = invs[0]["id"]
    client.post(f"/buddies/{link_id}/accept", headers={"Authorization": f"Bearer {b_tok}"})

    # Block
    r = client.post(f"/buddies/{link_id}/block", headers={"Authorization": f"Bearer {v_tok}"})
    assert r.status_code == 200

    # Verify blocked link no longer shows in active buddy list
    links = client.get("/buddies", headers={"Authorization": f"Bearer {v_tok}"}).json()
    active_ids = [l["id"] for l in links]
    assert link_id not in active_ids  # blocked links are excluded from the list
