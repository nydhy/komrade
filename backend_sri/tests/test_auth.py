"""Auth endpoint tests."""


def test_register_and_login_happy_path(client):
    """Register -> login -> /me works."""
    # Register
    reg = client.post(
        "/auth/register",
        json={
            "email": "veteran@test.com",
            "password": "secret123",
            "full_name": "Test Veteran",
            "role": "veteran",
        },
    )
    assert reg.status_code == 200
    data = reg.json()
    assert data["email"] == "veteran@test.com"
    assert data["role"] == "veteran"
    assert "id" in data

    # Login
    login = client.post(
        "/auth/login",
        json={"email": "veteran@test.com", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    # /me
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "veteran@test.com"
    assert me.json()["role"] == "veteran"


def test_wrong_password_fails(client):
    """Wrong password returns 401."""
    client.post(
        "/auth/register",
        json={
            "email": "fail@test.com",
            "password": "right",
            "full_name": "Fail User",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "fail@test.com", "password": "wrong"},
    )
    assert login.status_code == 401


def test_me_requires_auth(client):
    """GET /auth/me returns 401 without token."""
    response = client.get("/auth/me")
    assert response.status_code == 401
