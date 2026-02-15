"""Manual integration test for Journey ladder generation via Ollama."""

from __future__ import annotations

import json
import os
import secrets

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
EMAIL = os.getenv("TEST_EMAIL", f"journey_{secrets.token_hex(4)}@example.com")
PASSWORD = os.getenv("TEST_PASSWORD", "Passw0rd!123")

TEST_INTAKE = {
    "anxiety_level": 7,
    "triggers": ["crowds", "loud noises", "being looked at"],
    "time_since_comfortable": "3-6 months ago",
    "end_goal": "having conversations with strangers",
    "interests": ["coffee", "fitness", "reading"],
    "energy_times": ["Late morning (9am-12pm)", "Afternoon (12-4pm)"],
    "location": "College Park, MD",
    "avoid_situations": "bars, loud venues",
    "challenge_count": 6,
}


def _register_or_login(client: httpx.Client) -> str:
    register_payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Journey Test User",
        "role": "veteran",
    }
    register_resp = client.post("/auth/register", json=register_payload)
    if register_resp.status_code not in (200, 201, 400):
        raise RuntimeError(f"Register failed: {register_resp.status_code} {register_resp.text}")

    login_resp = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if login_resp.status_code != 200:
        raise RuntimeError(f"Login failed: {login_resp.status_code} {login_resp.text}")

    token = login_resp.json().get("access_token")
    if not token:
        raise RuntimeError("Login response missing access_token")
    return token


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=180.0) as client:
        token = _register_or_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/journey/challenges/generate", json=TEST_INTAKE, headers=headers)

    print("Status:", resp.status_code)
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001
        print("Raw response:", resp.text)
        raise

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
