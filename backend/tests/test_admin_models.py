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
