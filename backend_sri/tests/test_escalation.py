"""Module 8 — Escalation + Cooldown tests."""

from unittest.mock import patch


def _setup_veteran_with_buddies(client, vet_email, buddy_prefix, num_buddies=5):
    """Create veteran + N accepted buddies. Returns v_token, b_tokens."""
    client.post(
        "/auth/register",
        json={"email": vet_email, "password": "pass", "full_name": "Vet", "role": "veteran"},
    )
    b_tokens = []
    for i in range(num_buddies):
        email = f"{buddy_prefix}{i}@test.com"
        client.post(
            "/auth/register",
            json={"email": email, "password": "pass", "full_name": f"B{i}", "role": "buddy"},
        )

    v_token = client.post("/auth/login", json={"email": vet_email, "password": "pass"}).json()["access_token"]

    for i in range(num_buddies):
        email = f"{buddy_prefix}{i}@test.com"
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": email},
        )
    for i in range(num_buddies):
        email = f"{buddy_prefix}{i}@test.com"
        b_tok = client.post("/auth/login", json={"email": email, "password": "pass"}).json()["access_token"]
        b_tokens.append(b_tok)
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_tok}"}).json()
        for inv in invs:
            if inv["status"] == "PENDING":
                client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_tok}"})
                break
        # Set buddy presence to AVAILABLE so they appear on radar
        client.post("/presence", headers={"Authorization": f"Bearer {b_tok}"}, json={"status": "AVAILABLE"})

    return v_token, b_tokens


def test_cooldown_blocks_rapid_sos(client):
    """Creating 2 SOS within cooldown window is blocked."""
    v_token, _ = _setup_veteran_with_buddies(client, "v_cool@test.com", "bc", 3)

    # First SOS succeeds
    r1 = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "MED"})
    assert r1.status_code == 200

    # Second SOS immediately: blocked by cooldown
    r2 = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "HIGH"})
    assert r2.status_code == 400
    assert "cooldown" in r2.json()["detail"].lower()


def test_cooldown_allows_after_window(client):
    """SOS creation is allowed if cooldown has expired (mock time)."""
    from datetime import datetime, timedelta, timezone
    from app.models.sos_alert import SosAlert

    v_token, _ = _setup_veteran_with_buddies(client, "v_cool2@test.com", "bc2", 3)

    # Create first SOS
    r1 = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "MED"})
    assert r1.status_code == 200
    sos_id = r1.json()["id"]

    # Manually set created_at to 7 hours ago
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    alert = db.get(SosAlert, sos_id)
    alert.created_at = datetime.now(timezone.utc) - timedelta(hours=7)
    db.commit()
    db.close()

    # Now second SOS should be allowed
    r2 = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "LOW"})
    assert r2.status_code == 200


def test_escalate_too_early_fails(client):
    """Cannot escalate before ESCALATE_AFTER_MIN."""
    v_token, _ = _setup_veteran_with_buddies(client, "v_esc1@test.com", "be1", 5)

    r = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "MED"})
    assert r.status_code == 200
    sos_id = r.json()["id"]

    # Escalate immediately should fail
    r2 = client.post(f"/sos/{sos_id}/escalate", headers={"Authorization": f"Bearer {v_token}"})
    assert r2.status_code == 400
    assert "wait" in r2.json()["detail"].lower()


def test_escalate_after_time_adds_recipients(client):
    """Escalation adds more recipients after the time window."""
    from datetime import datetime, timedelta, timezone
    from app.models.sos_alert import SosAlert

    v_token, _ = _setup_veteran_with_buddies(client, "v_esc2@test.com", "be2", 8)

    r = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "MED"})
    assert r.status_code == 200
    sos_id = r.json()["id"]
    initial_count = len(r.json()["recipients"])
    assert initial_count >= 3

    # Move created_at back 15 minutes
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    alert = db.get(SosAlert, sos_id)
    alert.created_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    db.commit()
    db.close()

    # Escalate
    r2 = client.post(f"/sos/{sos_id}/escalate", headers={"Authorization": f"Bearer {v_token}"})
    assert r2.status_code == 200
    new_count = len(r2.json()["recipients"])
    assert new_count > initial_count
    assert r2.json()["status"] == "ESCALATED"


def test_escalate_blocked_if_accepted(client):
    """Cannot escalate if a buddy already accepted."""
    from datetime import datetime, timedelta, timezone
    from app.models.sos_alert import SosAlert

    v_token, b_tokens = _setup_veteran_with_buddies(client, "v_esc3@test.com", "be3", 5)

    r = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "MED"})
    assert r.status_code == 200
    sos_id = r.json()["id"]

    # A buddy accepts
    client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"status": "ACCEPTED"},
    )

    # Move time back
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    alert = db.get(SosAlert, sos_id)
    alert.created_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    db.commit()
    db.close()

    r2 = client.post(f"/sos/{sos_id}/escalate", headers={"Authorization": f"Bearer {v_token}"})
    assert r2.status_code == 400
    assert "accepted" in r2.json()["detail"].lower()


def test_escalate_idempotent_no_more_buddies(client):
    """Escalation with no additional buddies available returns error."""
    from datetime import datetime, timedelta, timezone
    from app.models.sos_alert import SosAlert

    # Only 3 buddies = all already used in SOS
    v_token, _ = _setup_veteran_with_buddies(client, "v_esc4@test.com", "be4", 3)

    r = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "MED"})
    assert r.status_code == 200
    sos_id = r.json()["id"]

    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    alert = db.get(SosAlert, sos_id)
    alert.created_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    db.commit()
    db.close()

    r2 = client.post(f"/sos/{sos_id}/escalate", headers={"Authorization": f"Bearer {v_token}"})
    assert r2.status_code == 400
    assert "no additional" in r2.json()["detail"].lower()
