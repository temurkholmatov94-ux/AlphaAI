def register_user(client, email="person@example.test"):
    response = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "LongPassphrase123!secure"},
    )
    assert response.status_code == 201
    return response.json()


def verify_user(client, token):
    response = client.post("/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 200


def session_token(client, email="person@example.test"):
    response = client.post(
        "/v1/auth/login",
        json={"email": email, "password": "LongPassphrase123!secure"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_registration_and_verification_required(client):
    registered = register_user(client)
    assert registered["verification_required"] is True
    blocked = client.post(
        "/v1/auth/login",
        json={"email": "person@example.test", "password": "LongPassphrase123!secure"},
    )
    assert blocked.status_code == 403
    verify_user(client, registered["development_verification_token"])
    assert session_token(client)


def test_verified_user_gets_own_workspace(client):
    registered = register_user(client)
    verify_user(client, registered["development_verification_token"])
    token = session_token(client)
    response = client.get("/v1/organizations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["role"] == "owner"


def test_api_key_is_scoped_and_revocable(client):
    registered = register_user(client)
    verify_user(client, registered["development_verification_token"])
    token = session_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/v1/api-keys",
        headers=headers,
        json={"name": "Catalog read key", "scopes": ["models:read"]},
    )
    assert created.status_code == 201
    raw_key = created.json()["api_key"]
    assert raw_key.startswith("aai_live_")

    denied = client.get(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert denied.status_code == 403

    revoked = client.delete(f"/v1/api-keys/{created.json()['id']}", headers=headers)
    assert revoked.status_code == 204
    rejected = client.get(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert rejected.status_code == 401


def test_duplicate_email_and_weak_password_are_rejected(client):
    registered = register_user(client)
    verify_user(client, registered["development_verification_token"])
    duplicate = client.post(
        "/v1/auth/register",
        json={"email": "PERSON@example.test", "password": "LongPassphrase123!secure"},
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/v1/auth/register",
        json={"email": "weak@example.test", "password": "short"},
    )
    assert weak.status_code == 422
