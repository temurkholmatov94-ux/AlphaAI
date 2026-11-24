import pytest
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import AuditEvent, ModelRecord, User
from app.security import create_access_token


def admin_client(client, monkeypatch, email="admin@example.com"):
    monkeypatch.setenv("ALPHAAI_ADMIN_EMAILS", '["admin@example.com"]')
    get_settings.cache_clear()
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        user = User(
            email=email,
            password_hash="not-used-in-this-test",
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token, _ = create_access_token(user.id)
    finally:
        db.close()
        generator.close()
        get_settings.cache_clear()
    return client, {"Authorization": f"Bearer {token}"}


def insert_review_model():
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        db.add(
            ModelRecord(
                model_id="test-org/review-model",
                display_name="Review Model",
                provider="Hugging Face",
                source_url="https://huggingface.co/test-org/review-model",
                license_id="apache-2.0",
                license_status="unknown",
                access_method="download",
                availability_status="review-required",
                tasks=["text-generation"],
                modalities=["text"],
                weights_available=False,
            )
        )
        db.commit()
    finally:
        db.close()
        generator.close()


def test_admin_review_queue_requires_platform_admin(client, monkeypatch):
    insert_review_model()
    _, headers = admin_client(client, monkeypatch, email="ordinary@example.com")
    response = client.get("/v1/admin/models/review-queue", headers=headers)
    assert response.status_code == 403


def test_admin_can_review_and_publish_only_with_license_and_access_approval(client, monkeypatch):
    insert_review_model()
    _, headers = admin_client(client, monkeypatch)

    queue = client.get("/v1/admin/models/review-queue", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["model_id"] == "test-org/review-model"

    invalid = client.patch(
        "/v1/admin/models/test-org/review-model/review",
        headers=headers,
        json={
            "license_status": "unknown",
            "access_method": "download",
            "availability_status": "available",
        },
    )
    assert invalid.status_code == 422

    approved = client.patch(
        "/v1/admin/models/test-org/review-model/review",
        headers=headers,
        json={
            "license_status": "verified",
            "access_method": "download",
            "availability_status": "available",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["availability_status"] == "available"
    assert client.get("/v1/models/test-org/review-model").status_code == 200

    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        event = db.scalar(select(AuditEvent).where(AuditEvent.action == "model.reviewed"))
        assert event is not None
        assert event.resource_id == "test-org/review-model"
        assert event.details["after"]["license_status"] == "verified"
    finally:
        db.close()
        generator.close()


def test_non_admin_cannot_publish_model(client, monkeypatch):
    insert_review_model()
    _, headers = admin_client(client, monkeypatch, email="intruder@example.com")
    response = client.patch(
        "/v1/admin/models/test-org/review-model/review",
        headers=headers,
        json={
            "license_status": "verified",
            "access_method": "download",
            "availability_status": "available",
        },
    )
    assert response.status_code == 403


def test_admin_console_page_is_served(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert "AlphaAI" in response.text
    assert "Administrator access" in response.text
    assert "/v1/admin/models/review-queue" in response.text


def test_admin_provider_inventory_requires_admin(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ALPHAAI_ADMIN_EMAILS", '["admin@example.com"]')
    get_settings.cache_clear()
    response = client.get("/v1/admin/providers")
    assert response.status_code in {401, 403}


def test_admin_provider_inventory_never_exposes_credentials(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ALPHAAI_ADMIN_EMAILS", '["admin@example.com"]')
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-do-not-leak")
    monkeypatch.setenv("ALPHAAI_MODEL_ROUTES", '["alpha-fast=openai:gpt-test"]')
    get_settings.cache_clear()
    _, headers = admin_client(client, monkeypatch)
    response = client.get("/v1/admin/providers", headers=headers)
    assert response.status_code == 200
    body = response.text
    assert "test-secret-do-not-leak" not in body
    assert "alpha-fast" in body
    assert "configured" in body
    get_settings.cache_clear()


def test_compute_worker_lifecycle_and_hardware_heartbeat(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ALPHAAI_ADMIN_EMAILS", '["admin@example.com"]')
    get_settings.cache_clear()
    _, headers = admin_client(client, monkeypatch)
    created = client.post(
        "/v1/admin/workers",
        headers=headers,
        json={"name": "Test GPU worker"},
    )
    assert created.status_code == 201
    data = created.json()
    assert data["worker_id"].startswith("wkr_")
    assert data["worker_token"].startswith("aai_worker_")
    assert data["token_display"] == "shown-once"

    heartbeat = client.post(
        "/v1/workers/heartbeat",
        headers={"Authorization": "Bearer " + data["worker_token"]},
        json={
            "agent_version": "0.1.0",
            "os": "Linux",
            "architecture": "x86_64",
            "cpu_model": "Test CPU",
            "cpu_logical_cores": 16,
            "ram_total_mb": 32768,
            "ram_available_mb": 24000,
            "gpus": [{"name": "Test GPU", "vendor": "NVIDIA", "vram_mb": 24576}],
        },
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["accepted"] is True

    listed = client.get("/v1/admin/workers", headers=headers)
    assert listed.status_code == 200
    worker = listed.json()["items"][0]
    assert worker["worker_id"] == data["worker_id"]
    assert worker["status"] == "online"
    assert worker["hardware"]["gpus"][0]["vram_mb"] == 24576

    revoked = client.post(
        f"/v1/admin/workers/{data['worker_id']}/revoke",
        headers=headers,
    )
    assert revoked.status_code == 200
    rejected = client.post(
        "/v1/workers/heartbeat",
        headers={"Authorization": "Bearer " + data["worker_token"]},
        json={
            "agent_version": "0.1.0",
            "os": "Linux",
            "architecture": "x86_64",
            "cpu_logical_cores": 4,
            "ram_total_mb": 8192,
            "ram_available_mb": 4096,
            "gpus": [],
        },
    )
    assert rejected.status_code == 401
    get_settings.cache_clear()


def test_worker_heartbeat_rejects_invalid_hardware_bounds(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ALPHAAI_ADMIN_EMAILS", '["admin@example.com"]')
    get_settings.cache_clear()
    _, headers = admin_client(client, monkeypatch)
    created = client.post("/v1/admin/workers", headers=headers, json={"name": "Bound test worker"})
    token = created.json()["worker_token"]
    response = client.post(
        "/v1/workers/heartbeat",
        headers={"Authorization": "Bearer " + token},
        json={
            "agent_version": "0.1.0",
            "os": "Linux",
            "architecture": "x86_64",
            "cpu_logical_cores": 4,
            "ram_total_mb": 4096,
            "ram_available_mb": 8192,
            "gpus": [],
        },
    )
    assert response.status_code == 422
    get_settings.cache_clear()
