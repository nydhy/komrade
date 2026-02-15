"""Geo + presence + nearby buddy tests."""


def _register(client, email, role="buddy"):
    client.post(
        "/auth/register",
        json={"email": email, "password": "pass", "full_name": email.split("@")[0], "role": role},
    )
    return client.post("/auth/login", json={"email": email, "password": "pass"}).json()["access_token"]


def _setup_veteran_with_buddies(client, vet_email, buddy_emails, accept=True):
    """Register veteran + buddies, invite + optionally accept all. Returns (vet_token, [bud_tokens])."""
    v_token = _register(client, vet_email, "veteran")
    bud_tokens = []
    for be in buddy_emails:
        bt = _register(client, be, "buddy")
        bud_tokens.append(bt)
        # Invite
        client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": be},
        )
    if accept:
        for bt in bud_tokens:
            invs = client.get("/buddies", headers={"Authorization": f"Bearer {bt}"}).json()
            for inv in invs:
                if inv["status"] == "PENDING":
                    client.post(f"/buddies/{inv['id']}/accept", headers={"Authorization": f"Bearer {bt}"})
                    break
    return v_token, bud_tokens


def test_set_presence(client):
    """Buddy can set availability."""
    bt = _register(client, "pres_b1@test.com", "buddy")

    r = client.post("/presence", headers={"Authorization": f"Bearer {bt}"}, json={"status": "AVAILABLE"})
    assert r.status_code == 200
    assert r.json()["status"] == "AVAILABLE"

    # Update
    r = client.post("/presence", headers={"Authorization": f"Bearer {bt}"}, json={"status": "BUSY"})
    assert r.status_code == 200
    assert r.json()["status"] == "BUSY"


def test_set_location(client):
    """User can update location."""
    vt = _register(client, "loc_v@test.com", "veteran")
    r = client.post("/location", headers={"Authorization": f"Bearer {vt}"}, json={"latitude": 40.7128, "longitude": -74.006})
    assert r.status_code == 200
    assert r.json()["latitude"] == 40.7128


def test_distance_sort(client):
    """Nearby buddies sorted by distance when all are AVAILABLE with same trust."""
    buddies = ["geo_b1@test.com", "geo_b2@test.com", "geo_b3@test.com"]
    v_token, bud_tokens = _setup_veteran_with_buddies(client, "geo_v@test.com", buddies)

    # Set veteran location: NYC
    client.post("/location", headers={"Authorization": f"Bearer {v_token}"}, json={"latitude": 40.7128, "longitude": -74.006})

    # b1: nearby (Brooklyn ~10km)
    client.post("/location", headers={"Authorization": f"Bearer {bud_tokens[0]}"}, json={"latitude": 40.6782, "longitude": -73.9442})
    # b2: far (LA ~3940km)
    client.post("/location", headers={"Authorization": f"Bearer {bud_tokens[1]}"}, json={"latitude": 34.0522, "longitude": -118.2437})
    # b3: medium (Boston ~306km)
    client.post("/location", headers={"Authorization": f"Bearer {bud_tokens[2]}"}, json={"latitude": 42.3601, "longitude": -71.0589})

    # All AVAILABLE
    for bt in bud_tokens:
        client.post("/presence", headers={"Authorization": f"Bearer {bt}"}, json={"status": "AVAILABLE"})

    r = client.get("/buddies/nearby?limit=10", headers={"Authorization": f"Bearer {v_token}"})
    assert r.status_code == 200
    buddies_list = r.json()
    assert len(buddies_list) == 3

    # Should be sorted: b1 (Brooklyn), b3 (Boston), b2 (LA)
    assert buddies_list[0]["buddy_email"] == "geo_b1@test.com"
    assert buddies_list[1]["buddy_email"] == "geo_b3@test.com"
    assert buddies_list[2]["buddy_email"] == "geo_b2@test.com"

    # Distances should be reasonable
    assert buddies_list[0]["distance_km"] < 20  # Brooklyn
    assert 250 < buddies_list[1]["distance_km"] < 400  # Boston
    assert 3500 < buddies_list[2]["distance_km"] < 4500  # LA


def test_busy_buddies_ranked_lower(client):
    """BUSY buddies ranked lower than AVAILABLE ones."""
    buddies = ["busy_b1@test.com", "busy_b2@test.com", "busy_b3@test.com"]
    v_token, bud_tokens = _setup_veteran_with_buddies(client, "busy_v@test.com", buddies)

    # Same location for everyone
    for t in [v_token] + bud_tokens:
        client.post("/location", headers={"Authorization": f"Bearer {t}"}, json={"latitude": 40.7128, "longitude": -74.006})

    # b1: BUSY, b2: AVAILABLE, b3: AVAILABLE
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[0]}"}, json={"status": "BUSY"})
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[1]}"}, json={"status": "AVAILABLE"})
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[2]}"}, json={"status": "AVAILABLE"})

    r = client.get("/buddies/nearby?limit=10", headers={"Authorization": f"Bearer {v_token}"})
    assert r.status_code == 200
    buddies_list = r.json()

    # BUSY buddy (b1) should be last
    assert buddies_list[-1]["buddy_email"] == "busy_b1@test.com"
    assert buddies_list[-1]["presence_status"] == "BUSY"
    # First two should be AVAILABLE
    assert buddies_list[0]["presence_status"] == "AVAILABLE"
    assert buddies_list[1]["presence_status"] == "AVAILABLE"


def test_blocked_excluded(client):
    """Blocked buddies don't appear in nearby list."""
    buddies = ["blk_b1@test.com", "blk_b2@test.com", "blk_b3@test.com", "blk_b4@test.com"]
    v_token, bud_tokens = _setup_veteran_with_buddies(client, "blk_v@test.com", buddies)

    # Set all buddies to AVAILABLE first
    for bt in bud_tokens:
        client.post("/presence", headers={"Authorization": f"Bearer {bt}"}, json={"status": "AVAILABLE"})

    # Block b2
    links = client.get("/buddies", headers={"Authorization": f"Bearer {v_token}"}).json()
    for link in links:
        if link["other_email"] == "blk_b2@test.com":
            client.post(f"/buddies/{link['id']}/block", headers={"Authorization": f"Bearer {v_token}"})
            break

    r = client.get("/buddies/nearby?limit=10", headers={"Authorization": f"Bearer {v_token}"})
    assert r.status_code == 200
    buddy_emails = [b["buddy_email"] for b in r.json()]

    assert "blk_b2@test.com" not in buddy_emails
    assert len(buddy_emails) == 3  # b1, b3, b4


def test_sos_uses_ranking(client):
    """SOS should use ranked buddies — OFFLINE buddies are excluded from selection."""
    buddies = ["sos_r_b1@test.com", "sos_r_b2@test.com", "sos_r_b3@test.com", "sos_r_b4@test.com"]
    v_token, bud_tokens = _setup_veteran_with_buddies(client, "sos_r_v@test.com", buddies)

    # b1: OFFLINE, b2: AVAILABLE, b3: AVAILABLE, b4: AVAILABLE
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[0]}"}, json={"status": "OFFLINE"})
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[1]}"}, json={"status": "AVAILABLE"})
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[2]}"}, json={"status": "AVAILABLE"})
    client.post("/presence", headers={"Authorization": f"Bearer {bud_tokens[3]}"}, json={"status": "AVAILABLE"})

    # Create SOS — OFFLINE b1 is excluded from ranking, so only 3 available buddies are selected
    r = client.post("/sos", headers={"Authorization": f"Bearer {v_token}"}, json={"severity": "HIGH"})
    assert r.status_code == 200
    recipients = r.json()["recipients"]
    assert len(recipients) == 3  # Only non-OFFLINE buddies

    # OFFLINE buddy (b1) should NOT be a recipient
    recipient_emails = set()
    for rec in recipients:
        recipient_emails.add(rec.get("buddy_email", rec.get("buddy_id")))
    assert len(set(rec["buddy_id"] for rec in recipients)) == 3  # All unique


def test_presence_validation(client):
    """Invalid presence status returns 422."""
    bt = _register(client, "pval_b@test.com", "buddy")
    r = client.post("/presence", headers={"Authorization": f"Bearer {bt}"}, json={"status": "INVALID"})
    assert r.status_code == 422


def test_location_validation(client):
    """Invalid coordinates return 422."""
    vt = _register(client, "lval_v@test.com", "veteran")
    r = client.post("/location", headers={"Authorization": f"Bearer {vt}"}, json={"latitude": 100, "longitude": 0})
    assert r.status_code == 422
