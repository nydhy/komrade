"""Buddy links API tests."""


def test_any_user_can_invite(client):
    """Any user (not just veterans) can invite buddies. Bidirectional buddy system."""
    # Register as buddy (not veteran)
    client.post(
        "/auth/register",
        json={
            "email": "buddy@test.com",
            "password": "pass123",
            "full_name": "Buddy User",
            "role": "buddy",
        },
    )
    login = client.post("/auth/login", json={"email": "buddy@test.com", "password": "pass123"})
    token = login.json()["access_token"]

    # Register veteran
    client.post(
        "/auth/register",
        json={
            "email": "veteran@test.com",
            "password": "pass123",
            "full_name": "Veteran User",
            "role": "veteran",
        },
    )

    # Buddy invites veteran - should now succeed (bidirectional)
    resp = client.post(
        "/buddies/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"buddy_email": "veteran@test.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"


def test_bidirectional_duplicate_blocked(client):
    """If A invites B, B cannot also invite A (duplicate detection)."""
    client.post(
        "/auth/register",
        json={"email": "u1@test.com", "password": "pass", "full_name": "U1", "role": "veteran"},
    )
    client.post(
        "/auth/register",
        json={"email": "u2@test.com", "password": "pass", "full_name": "U2", "role": "buddy"},
    )

    t1 = client.post("/auth/login", json={"email": "u1@test.com", "password": "pass"}).json()["access_token"]
    t2 = client.post("/auth/login", json={"email": "u2@test.com", "password": "pass"}).json()["access_token"]

    # U1 invites U2
    resp1 = client.post("/buddies/invite", headers={"Authorization": f"Bearer {t1}"}, json={"buddy_email": "u2@test.com"})
    assert resp1.status_code == 200

    # U2 tries to invite U1 - should get 400 (already pending)
    resp2 = client.post("/buddies/invite", headers={"Authorization": f"Bearer {t2}"}, json={"buddy_email": "u1@test.com"})
    assert resp2.status_code == 400
    assert "pending" in resp2.json()["detail"].lower()


def test_only_invited_buddy_can_accept(client):
    """Only the invited buddy can accept an invite."""
    # Register veteran and buddy
    client.post(
        "/auth/register",
        json={"email": "v1@test.com", "password": "pass", "full_name": "V1", "role": "veteran"},
    )
    client.post(
        "/auth/register",
        json={"email": "b1@test.com", "password": "pass", "full_name": "B1", "role": "buddy"},
    )
    client.post(
        "/auth/register",
        json={"email": "b2@test.com", "password": "pass", "full_name": "B2", "role": "buddy"},
    )

    v_token = client.post("/auth/login", json={"email": "v1@test.com", "password": "pass"}).json()["access_token"]
    b2_token = client.post("/auth/login", json={"email": "b2@test.com", "password": "pass"}).json()["access_token"]

    # Veteran invites b1
    inv = client.post(
        "/buddies/invite",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"buddy_email": "b1@test.com"},
    )
    assert inv.status_code == 200
    link_id = inv.json()["id"]

    # B2 (not invited) tries to accept - should fail
    resp = client.post(
        f"/buddies/{link_id}/accept",
        headers={"Authorization": f"Bearer {b2_token}"},
    )
    assert resp.status_code == 400


def test_invite_accept_flow(client):
    """Invite -> buddy sees pending -> accept -> veteran sees accepted."""
    # Register users
    client.post(
        "/auth/register",
        json={"email": "vet@test.com", "password": "pass", "full_name": "Vet", "role": "veteran"},
    )
    client.post(
        "/auth/register",
        json={"email": "bud@test.com", "password": "pass", "full_name": "Bud", "role": "buddy"},
    )

    v_token = client.post("/auth/login", json={"email": "vet@test.com", "password": "pass"}).json()["access_token"]
    b_token = client.post("/auth/login", json={"email": "bud@test.com", "password": "pass"}).json()["access_token"]

    # Veteran invites buddy
    inv = client.post(
        "/buddies/invite",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"buddy_email": "bud@test.com"},
    )
    assert inv.status_code == 200
    link_id = inv.json()["id"]

    # Buddy sees pending
    b_list = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"})
    assert b_list.status_code == 200
    links = b_list.json()
    assert len(links) == 1
    assert links[0]["status"] == "PENDING"

    # Buddy accepts
    acc = client.post(f"/buddies/{link_id}/accept", headers={"Authorization": f"Bearer {b_token}"})
    assert acc.status_code == 200
    assert acc.json()["status"] == "ACCEPTED"

    # Veteran sees accepted buddy
    v_list = client.get("/buddies", headers={"Authorization": f"Bearer {v_token}"})
    assert v_list.status_code == 200
    assert any(l["status"] == "ACCEPTED" for l in v_list.json())

    # Buddy sees accepted connection (veteran) in My Buddies
    b_list = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"})
    assert b_list.status_code == 200
    assert len(b_list.json()) == 1
    assert b_list.json()[0]["status"] == "ACCEPTED"
    assert b_list.json()[0]["other_email"] == "vet@test.com"


def test_buddy_list_includes_location(client):
    """Accepted buddies show each other's location in the buddy list."""
    client.post(
        "/auth/register",
        json={"email": "loc_v@test.com", "password": "pass", "full_name": "LocV", "role": "veteran",
               "latitude": 40.7128, "longitude": -74.0060},
    )
    client.post(
        "/auth/register",
        json={"email": "loc_b@test.com", "password": "pass", "full_name": "LocB", "role": "buddy",
               "latitude": 34.0522, "longitude": -118.2437},
    )

    v_token = client.post("/auth/login", json={"email": "loc_v@test.com", "password": "pass"}).json()["access_token"]
    b_token = client.post("/auth/login", json={"email": "loc_b@test.com", "password": "pass"}).json()["access_token"]

    # Invite & accept
    inv = client.post("/buddies/invite", headers={"Authorization": f"Bearer {v_token}"}, json={"buddy_email": "loc_b@test.com"})
    link_id = inv.json()["id"]
    client.post(f"/buddies/{link_id}/accept", headers={"Authorization": f"Bearer {b_token}"})

    # Veteran sees buddy's location
    v_list = client.get("/buddies", headers={"Authorization": f"Bearer {v_token}"})
    accepted = [l for l in v_list.json() if l["status"] == "ACCEPTED"]
    assert len(accepted) == 1
    assert accepted[0]["other_latitude"] == 34.0522
    assert accepted[0]["other_longitude"] == -118.2437

    # Buddy sees veteran's location
    b_list = client.get("/buddies", headers={"Authorization": f"Bearer {b_token}"})
    accepted_b = [l for l in b_list.json() if l["status"] == "ACCEPTED"]
    assert len(accepted_b) == 1
    assert accepted_b[0]["other_latitude"] == 40.7128
    assert accepted_b[0]["other_longitude"] == -74.0060


def test_block_removes_from_list(client):
    """Blocked links do not appear in buddy list."""
    client.post(
        "/auth/register",
        json={"email": "v@test.com", "password": "pass", "full_name": "V", "role": "veteran"},
    )
    client.post(
        "/auth/register",
        json={"email": "b@test.com", "password": "pass", "full_name": "B", "role": "buddy"},
    )

    v_token = client.post("/auth/login", json={"email": "v@test.com", "password": "pass"}).json()["access_token"]
    b_token = client.post("/auth/login", json={"email": "b@test.com", "password": "pass"}).json()["access_token"]

    inv = client.post(
        "/buddies/invite",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"buddy_email": "b@test.com"},
    )
    link_id = inv.json()["id"]

    # Block
    client.post(f"/buddies/{link_id}/block", headers={"Authorization": f"Bearer {v_token}"})

    # Veteran's list should not include blocked
    v_list = client.get("/buddies", headers={"Authorization": f"Bearer {v_token}"})
    assert v_list.status_code == 200
    assert len(v_list.json()) == 0
