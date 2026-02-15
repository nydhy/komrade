"""
Module 10 — End-to-End Demo Test.

Full flow: Veteran + 3 buddies → check-in → SOS → buddy responds → veteran sees update → escalate → close.
"""


def test_full_demo_flow(client):
    """Complete E2E flow simulating the hackathon demo."""

    # ======== 1. REGISTER users ========
    vet = client.post(
        "/auth/register",
        json={"email": "demo_vet@test.com", "password": "pass", "full_name": "Demo Veteran", "role": "veteran"},
    )
    assert vet.status_code == 200

    buddies = []
    for i in range(4):
        r = client.post(
            "/auth/register",
            json={"email": f"demo_buddy{i}@test.com", "password": "pass", "full_name": f"Demo Buddy {i}", "role": "buddy"},
        )
        assert r.status_code == 200
        buddies.append(r.json())

    # ======== 2. LOGIN ========
    v_token = client.post("/auth/login", json={"email": "demo_vet@test.com", "password": "pass"}).json()["access_token"]
    b_tokens = []
    for i in range(4):
        tok = client.post("/auth/login", json={"email": f"demo_buddy{i}@test.com", "password": "pass"}).json()["access_token"]
        b_tokens.append(tok)

    # ======== 3. AUTH /me ========
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {v_token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "veteran"

    # ======== 4. BUDDY INVITE + ACCEPT ========
    for i in range(4):
        inv = client.post(
            "/buddies/invite",
            headers={"Authorization": f"Bearer {v_token}"},
            json={"buddy_email": f"demo_buddy{i}@test.com"},
        )
        assert inv.status_code == 200

    for i in range(4):
        invs = client.get("/buddies", headers={"Authorization": f"Bearer {b_tokens[i]}"}).json()
        for link in invs:
            if link["status"] == "PENDING":
                accept = client.post(f"/buddies/{link['id']}/accept", headers={"Authorization": f"Bearer {b_tokens[i]}"})
                assert accept.status_code == 200
                break

    buddy_links = client.get("/buddies", headers={"Authorization": f"Bearer {v_token}"}).json()
    accepted = [l for l in buddy_links if l["status"] == "ACCEPTED"]
    assert len(accepted) == 4

    # ======== 5. PRESENCE + LOCATION ========
    for i in range(4):
        r = client.post(
            "/presence",
            headers={"Authorization": f"Bearer {b_tokens[i]}"},
            json={"status": "AVAILABLE"},
        )
        assert r.status_code == 200

    r = client.post(
        "/location",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"latitude": 37.7749, "longitude": -122.4194},
    )
    assert r.status_code == 200

    # ======== 6. NEARBY BUDDIES ========
    nearby = client.get("/buddies/nearby?limit=10", headers={"Authorization": f"Bearer {v_token}"})
    assert nearby.status_code == 200
    assert len(nearby.json()) >= 4

    # ======== 7. MOOD CHECK-IN (low mood) ========
    checkin = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {v_token}"},
        json={"mood_score": 1, "tags": ["anxious", "sad"], "wants_company": True},
    )
    assert checkin.status_code == 200
    checkin_id = checkin.json()["id"]
    assert checkin.json()["mood_score"] == 1

    checkins = client.get("/checkins/me?limit=5", headers={"Authorization": f"Bearer {v_token}"})
    assert checkins.status_code == 200
    assert len(checkins.json()) >= 1

    # ======== 8. SOS FROM CHECK-IN ========
    sos = client.post(
        f"/sos/from-checkin/{checkin_id}",
        headers={"Authorization": f"Bearer {v_token}"},
    )
    assert sos.status_code == 200
    sos_data = sos.json()
    sos_id = sos_data["id"]
    assert sos_data["trigger_type"] == "MOOD"
    assert sos_data["status"] == "OPEN"
    assert len(sos_data["recipients"]) >= 3

    # ======== 9. BUDDY INBOX ========
    incoming = client.get("/sos/incoming", headers={"Authorization": f"Bearer {b_tokens[0]}"})
    assert incoming.status_code == 200
    # Should have at least one alert
    assert len(incoming.json()) >= 1

    # ======== 10. BUDDY RESPONDS (ACCEPT) ========
    accept_resp = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"status": "ACCEPTED", "message": "On my way!", "eta_minutes": 15},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "ACCEPTED"

    # ======== 11. ANOTHER BUDDY DECLINES ========
    decline_resp = client.post(
        f"/sos/{sos_id}/respond",
        headers={"Authorization": f"Bearer {b_tokens[1]}"},
        json={"status": "DECLINED", "message": "Sorry, can't make it"},
    )
    assert decline_resp.status_code == 200
    assert decline_resp.json()["status"] == "DECLINED"

    # ======== 12. VETERAN SEES UPDATED TIMELINE ========
    timeline = client.get(f"/sos/{sos_id}", headers={"Authorization": f"Bearer {v_token}"})
    assert timeline.status_code == 200
    recipients = timeline.json()["recipients"]
    statuses = {r["status"] for r in recipients}
    assert "ACCEPTED" in statuses
    assert "DECLINED" in statuses

    # ======== 13. VETERAN LISTS SOS ALERTS ========
    my_sos = client.get("/sos/me", headers={"Authorization": f"Bearer {v_token}"})
    assert my_sos.status_code == 200
    assert len(my_sos.json()) >= 1

    # ======== 14. SETTINGS ========
    settings = client.get("/settings/me", headers={"Authorization": f"Bearer {b_tokens[0]}"})
    assert settings.status_code == 200

    update = client.put(
        "/settings/me",
        headers={"Authorization": f"Bearer {b_tokens[0]}"},
        json={"quiet_hours_start": "23:00", "quiet_hours_end": "06:00", "share_precise_location": False},
    )
    assert update.status_code == 200
    assert update.json()["quiet_hours_start"] == "23:00"

    # ======== 15. CLOSE SOS ========
    close = client.post(f"/sos/{sos_id}/close", headers={"Authorization": f"Bearer {v_token}"})
    assert close.status_code == 200
    assert close.json()["status"] == "CLOSED"
    assert close.json()["closed_at"] is not None

    # ======== 16. VERIFY CLOSED ========
    final = client.get(f"/sos/{sos_id}", headers={"Authorization": f"Bearer {v_token}"})
    assert final.json()["status"] == "CLOSED"

    # ======== DONE ========
    # Full E2E flow passed: register → login → invite → accept → presence →
    # location → nearby → check-in → SOS → inbox → respond → timeline →
    # settings → close
