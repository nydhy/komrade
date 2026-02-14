"""SOS alerts API tests."""


def test_sos_requires_at_least_one_accepted_buddy(client):
    """SOS creation fails if veteran has no accepted buddies."""
    client.post(
        "/auth/register",
        json={"email": "v_few@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )

    v_token = client.post("/auth/login", json={"email": "v_few@test.com", "password": "pass"}).json()["access_token"]

    r = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"severity": "MED"},
    )
    assert r.status_code == 400
    assert "1" in r.json().get("detail", "") or "buddy" in r.json().get("detail", "").lower()


def test_sos_works_with_one_buddy(client):
    """SOS creation succeeds with exactly 1 accepted buddy (minimum)."""
    client.post(
        "/auth/register",
        json={"email": "v_one@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    client.post(
        "/auth/register",
        json={"email": "b_one@test.com", "password": "pass", "full_name": "B", "role": "buddy"},
    )

    v_token = client.post("/auth/login", json={"email": "v_one@test.com", "password": "pass"}).json()["access_token"]
    b_token = client.post("/auth/login", json={"email": "b_one@test.com", "password": "pass"}).json()["access_token"]

    client.post(
        "/buddies/invite",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"buddy_email": "b_one@test.com"},
    )
    invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"}).json()
    for inv in invs:
        if inv["status"] == "PENDING":
            client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_token}"})
            client.post("/presence", headers={"Authorization": f"Bearer {b_token}"}, json={"status": "AVAILABLE"})
            break

    r = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"severity": "MED"},
    )
    assert r.status_code == 200
    assert len(r.json()["recipients"]) == 1


def test_only_veteran_can_create_sos(client):
    """Non-veteran cannot create SOS."""
    client.post(
        "/auth/register",
        json={"email": "buddy_sos@test.com", "password": "pass", "full_name": "B", "role": "buddy"},
    )
    token = client.post("/auth/login", json={"email": "buddy_sos@test.com", "password": "pass"}).json()["access_token"]

    r = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {token}"},
        json={"severity": "MED"},
    )
    assert r.status_code == 403


def test_sos_picks_only_accepted_buddies(client):
    """SOS creates recipients only from ACCEPTED buddies, not blocked/pending."""
    # Veteran + 3 buddies
    client.post(
        "/auth/register",
        json={"email": "v@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    for i in range(4):
        client.post(
            "/auth/register",
            json={"email": f"b{i}@test.com", "password": "pass", "full_name": f"B{i}", "role": "buddy"},
        )

    v_token = client.post("/auth/login", json={"email": "v@test.com", "password": "pass"}).json()["access_token"]
    b0_token = client.post("/auth/login", json={"email": "b0@test.com", "password": "pass"}).json()["access_token"]
    b1_token = client.post("/auth/login", json={"email": "b1@test.com", "password": "pass"}).json()["access_token"]
    b2_token = client.post("/auth/login", json={"email": "b2@test.com", "password": "pass"}).json()["access_token"]

    # Veteran invites b0, b1, b2, b3
    for i in range(4):
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": f"b{i}@test.com"},
        )

    # b0, b1, b2 accept; b3 stays pending
    invs = client.get("/buddies", headers={"Authorization": f"Bearer {b0_token}"}).json()
    for inv in invs:
        if inv["status"] == "PENDING":
            link_id = inv["id"]
            client.post(f"/buddies/{link_id}/accept", headers={"Authorization": f"Bearer {b0_token}"})
            client.post("/presence", headers={"Authorization": f"Bearer {b0_token}"}, json={"status": "AVAILABLE"})
            break
    invs = client.get("/buddies", headers={"Authorization": f"Bearer {b1_token}"}).json()
    for inv in invs:
        if inv["status"] == "PENDING":
            link_id = inv["id"]
            client.post(f"/buddies/{link_id}/accept", headers={"Authorization": f"Bearer {b1_token}"})
            client.post("/presence", headers={"Authorization": f"Bearer {b1_token}"}, json={"status": "AVAILABLE"})
            break
    invs = client.get("/buddies", headers={"Authorization": f"Bearer {b2_token}"}).json()
    for inv in invs:
        if inv["status"] == "PENDING":
            link_id = inv["id"]
            client.post(f"/buddies/{link_id}/accept", headers={"Authorization": f"Bearer {b2_token}"})
            client.post("/presence", headers={"Authorization": f"Bearer {b2_token}"}, json={"status": "AVAILABLE"})
            break

    # Veteran creates SOS - should have exactly 3 recipients (b0, b1, b2 - not b3 pending)
    r = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"severity": "MED"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "OPEN"
    assert data["trigger_type"] == "MANUAL"
    assert len(data["recipients"]) == 3
    buddy_ids = {rec["buddy_id"] for rec in data["recipients"]}
    # b3 is pending so should NOT be in recipients
    assert len(buddy_ids) == 3


def test_sos_creates_exactly_n_recipients(client):
    """SOS creates 3-5 recipients. With 5 accepted buddies, creates 5."""
    client.post(
        "/auth/register",
        json={"email": "v_sos@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    for i in range(5):
        client.post(
            "/auth/register",
            json={"email": f"bud_sos{i}@test.com", "password": "pass", "full_name": f"B{i}", "role": "buddy"},
        )

    v_token = client.post("/auth/login", json={"email": "v_sos@test.com", "password": "pass"}).json()["access_token"]

    # Invite and accept all 5
    for i in range(5):
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": f"bud_sos{i}@test.com"},
        )
    for i in range(5):
        b_token = client.post("/auth/login", json={"email": f"bud_sos{i}@test.com", "password": "pass"}).json()["access_token"]
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"}).json()
        for inv in invs:
            if inv["status"] == "PENDING":
                client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_token}"})
                client.post("/presence", headers={"Authorization": f"Bearer {b_token}"}, json={"status": "AVAILABLE"})
                break

    r = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"severity": "HIGH"},
    )
    assert r.status_code == 200
    assert len(r.json()["recipients"]) == 5


def test_close_requires_owner_veteran(client):
    """Only veteran who created SOS can close it."""
    client.post(
        "/auth/register",
        json={"email": "v1@test.com", "password": "pass", "full_name": "V1", "role": "veteran"},
    )
    client.post(
        "/auth/register",
        json={"email": "v2@test.com", "password": "pass", "full_name": "V2", "role": "veteran"},
    )
    for i in range(3):
        client.post(
            "/auth/register",
            json={"email": f"b_close{i}@test.com", "password": "pass", "full_name": f"B{i}", "role": "buddy"},
        )

    v1_token = client.post("/auth/login", json={"email": "v1@test.com", "password": "pass"}).json()["access_token"]
    v2_token = client.post("/auth/login", json={"email": "v2@test.com", "password": "pass"}).json()["access_token"]

    # V1 invites buddies and they accept
    for i in range(3):
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v1_token}"},
            json={"buddy_email": f"b_close{i}@test.com"},
        )
    for i in range(3):
        b_token = client.post("/auth/login", json={"email": f"b_close{i}@test.com", "password": "pass"}).json()["access_token"]
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"}).json()
        for inv in invs:
            if inv["status"] == "PENDING":
                client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_token}"})
                client.post("/presence", headers={"Authorization": f"Bearer {b_token}"}, json={"status": "AVAILABLE"})
                break

    # V1 creates SOS
    create = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v1_token}"},
        json={"severity": "MED"},
    )
    assert create.status_code == 200
    sos_id = create.json()["id"]

    # V2 tries to close - should fail 403
    r = client.post(
        f"/sos/{sos_id}/close",
        headers={"Authorization": f"Bearer {v2_token}"},
    )
    assert r.status_code == 403

    # V1 closes - should succeed
    r = client.post(
        f"/sos/{sos_id}/close",
        headers={"Authorization": f"Bearer {v1_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"
    assert r.json()["closed_at"] is not None


def test_sos_from_checkin_wants_company(client):
    """Create SOS from check-in when wants_company is true."""
    client.post(
        "/auth/register",
        json={"email": "v_chk@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    for i in range(3):
        client.post(
            "/auth/register",
            json={"email": f"b_chk{i}@test.com", "password": "pass", "full_name": f"B{i}", "role": "buddy"},
        )

    v_token = client.post("/auth/login", json={"email": "v_chk@test.com", "password": "pass"}).json()["access_token"]
    for i in range(3):
        b_token = client.post("/auth/login", json={"email": f"b_chk{i}@test.com", "password": "pass"}).json()["access_token"]
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": f"b_chk{i}@test.com"},
        )
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"}).json()
        for inv in invs:
            if inv["status"] == "PENDING":
                client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_token}"})
                client.post("/presence", headers={"Authorization": f"Bearer {b_token}"}, json={"status": "AVAILABLE"})
                break

    # Create check-in with wants_company
    checkin = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"mood_score": 4, "tags": [], "wants_company": True},
    )
    assert checkin.status_code == 200
    checkin_id = checkin.json()["id"]

    r = client.post(
        f"/sos/from-checkin/{checkin_id}",
        headers={"Authorization": f"Bearer {v_token}"},
    )
    assert r.status_code == 200
    assert r.json()["trigger_type"] == "MOOD"
    assert len(r.json()["recipients"]) == 3


def test_veteran_can_view_own_sos(client):
    """Veteran can view SOS status."""
    client.post(
        "/auth/register",
        json={"email": "v_view@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    for i in range(3):
        client.post(
            "/auth/register",
            json={"email": f"b_view{i}@test.com", "password": "pass", "full_name": f"B{i}", "role": "buddy"},
        )

    v_token = client.post("/auth/login", json={"email": "v_view@test.com", "password": "pass"}).json()["access_token"]
    for i in range(3):
        b_token = client.post("/auth/login", json={"email": f"b_view{i}@test.com", "password": "pass"}).json()["access_token"]
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": f"b_view{i}@test.com"},
        )
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"}).json()
        for inv in invs:
            if inv["status"] == "PENDING":
                client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {b_token}"})
                client.post("/presence", headers={"Authorization": f"Bearer {b_token}"}, json={"status": "AVAILABLE"})
                break

    create = client.post(
        "/sos",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"severity": "LOW"},
    )
    sos_id = create.json()["id"]

    r = client.get(f"/sos/{sos_id}", headers={"Authorization": f"Bearer {v_token}"})
    assert r.status_code == 200
    assert r.json()["id"] == sos_id
    assert r.json()["status"] == "OPEN"
    assert len(r.json()["recipients"]) == 3
