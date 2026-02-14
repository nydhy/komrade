"""Module 6 — Buddy Inbox + Respond tests."""

import uuid


def _unique():
    return uuid.uuid4().hex[:6]


def _setup_sos(client):
    """Create a veteran with 3 accepted buddies + an SOS alert. Return tokens + sos data."""
    uid = _unique()
    v_email = f"v_inb_{uid}@test.com"
    client.post(
        "/auth/register",
        json={"email": v_email, "password": "pass", "full_name": "Vet Inbox", "role": "veteran"},
    )
    b_emails = []
    for i in range(3):
        email = f"b_inb{i}_{uid}@test.com"
        b_emails.append(email)
        client.post(
            "/auth/register",
            json={"email": email, "password": "pass", "full_name": f"Buddy {i}", "role": "buddy"},
        )

    v_token = client.post("/auth/login", json={"email": v_email, "password": "pass"}).json()["access_token"]

    b_tokens = []
    for email in b_emails:
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": email},
        )
    for email in b_emails:
        b_tok = client.post("/auth/login", json={"email": email, "password": "pass"}).json()["access_token"]
        b_tokens.append(b_tok)
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_tok}"}).json()
        for inv in invs:
            if inv["status"] == "PENDING":
                client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_tok}"})
                break
        # Set buddy presence to AVAILABLE so they appear on radar
        client.post("/presence", headers={"Authorization": f"Bearer {b_tok}"}, json={"status": "AVAILABLE"})

    # Create SOS
    sos = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"severity": "MED"},
    )
    assert sos.status_code == 200, f"SOS creation failed: {sos.json()}"
    return v_token, b_tokens, sos.json()


def test_buddy_sees_incoming_alerts(client):
    """Buddy can see incoming SOS alerts via GET /sos/incoming."""
    _, b_tokens, sos_data = _setup_sos(client)

    for b_tok in b_tokens:
        incoming = client.get("/sos/incoming", headers={"Authorization": f"Bearer {b_tok}"}).json()
        if any(inc["alert_id"] == sos_data["id"] for inc in incoming):
            alert_entry = next(inc for inc in incoming if inc["alert_id"] == sos_data["id"])
            assert alert_entry["my_status"] == "NOTIFIED"
            assert alert_entry["veteran_name"] == "Vet Inbox"
            assert alert_entry["severity"] == "MED"


def test_buddy_can_accept(client):
    """Buddy can accept an SOS alert with message and ETA."""
    v_token, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"status": "ACCEPTED", "message": "On my way!", "eta_minutes": 15},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ACCEPTED"
    assert data["message"] == "On my way!"
    assert data["eta_minutes"] == 15
    assert data["responded_at"] is not None


def test_buddy_can_decline(client):
    """Buddy can decline an SOS alert."""
    _, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[1]}"},
        json={"status": "DECLINED", "message": "Sorry, not available right now"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "DECLINED"
    assert data["message"] == "Sorry, not available right now"


def test_only_recipient_can_respond(client):
    """Non-recipient buddy gets 403 when trying to respond."""
    _, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]

    uid = _unique()
    client.post(
        "/auth/register",
        json={"email": f"outsider_{uid}@test.com", "password": "pass", "full_name": "Outsider", "role": "buddy"},
    )
    outsider_token = client.post("/auth/login", json={"email": f"outsider_{uid}@test.com", "password": "pass"}).json()["access_token"]

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {outsider_token}"},
        json={"status": "ACCEPTED"},
    )
    assert r.status_code == 403
    assert "not a recipient" in r.json()["detail"].lower()


def test_double_respond_is_idempotent(client):
    """Responding twice updates the response (idempotent), doesn't error."""
    _, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]
    tok = b_tokens[0]

    r1 = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "ACCEPTED", "message": "Coming!", "eta_minutes": 30},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "ACCEPTED"
    assert r1.json()["eta_minutes"] == 30

    r2 = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "DECLINED", "message": "Can't make it after all"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "DECLINED"
    assert r2.json()["message"] == "Can't make it after all"
    assert r2.json()["eta_minutes"] is None


def test_eta_validation_range(client):
    """ETA must be 1-120 if provided."""
    _, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]
    tok = b_tokens[0]

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "ACCEPTED", "eta_minutes": 0},
    )
    assert r.status_code == 422

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "ACCEPTED", "eta_minutes": 121},
    )
    assert r.status_code == 422

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "ACCEPTED", "eta_minutes": 1},
    )
    assert r.status_code == 200
    assert r.json()["eta_minutes"] == 1

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "ACCEPTED", "eta_minutes": 120},
    )
    assert r.status_code == 200
    assert r.json()["eta_minutes"] == 120


def test_respond_to_closed_sos_fails(client):
    """Cannot respond to a closed SOS alert."""
    v_token, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]

    close = client.post(f"/sos/{sos_id}/close", headers={"Authorization": f"Bearer {v_token}"})
    assert close.status_code == 200

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"status": "ACCEPTED"},
    )
    assert r.status_code == 400
    assert "closed" in r.json()["detail"].lower()


def test_veteran_sees_updated_timeline(client):
    """After buddy responds, veteran sees updated recipient status."""
    v_token, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]

    client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"status": "ACCEPTED", "message": "On my way!", "eta_minutes": 10},
    )

    r = client.get(f"/sos/{sos_id}", headers={"Authorization": f"Bearer {v_token}"})
    assert r.status_code == 200
    data = r.json()

    accepted = [rec for rec in data["recipients"] if rec["status"] == "ACCEPTED"]
    assert len(accepted) == 1
    assert accepted[0]["message"] == "On my way!"
    assert accepted[0]["eta_minutes"] == 10


def test_respond_status_validation(client):
    """Status must be ACCEPTED or DECLINED."""
    _, b_tokens, sos_data = _setup_sos(client)
    sos_id = sos_data["id"]

    r = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"status": "MAYBE"},
    )
    assert r.status_code == 422
