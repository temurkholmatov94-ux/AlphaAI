from app.database import get_db
from app.main import app
from app.models import ModelRecord


def insert_model(**values):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(ModelRecord(**values))
        db.commit()
    finally:
        db.close()
        db_generator.close()


def test_public_registry_is_empty_without_database_records(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_model_list_hides_unreviewed_and_unlicensed_records(client):
    insert_model(
        model_id="alpha/test-chat",
        display_name="Test Chat",
        provider="Alpha",
        license_status="verified",
        access_method="hosted_api",
        availability_status="available",
        tasks=["text-generation"],
        modalities=["text"],
    )
    insert_model(
        model_id="alpha/private-preview",
        display_name="Private Preview",
        provider="Alpha",
        license_status="unknown",
        availability_status="review-required",
        tasks=["text-generation"],
        modalities=["text"],
    )
    insert_model(
        model_id="alpha/license-pending",
        display_name="License Pending",
        provider="Alpha",
        license_status="unknown",
        access_method="hosted_api",
        availability_status="available",
        tasks=["text-generation"],
        modalities=["text"],
    )

    response = client.get("/v1/models?q=Test")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["model_id"] == "alpha/test-chat"
    assert client.get("/v1/models/alpha/private-preview").status_code == 404
    assert client.get("/v1/models/alpha/license-pending").status_code == 404


def test_model_detail_supports_provider_slash_ids(client):
    insert_model(
        model_id="org/detail-model",
        display_name="Detail Model",
        provider="Alpha",
        license_status="verified",
        access_method="hosted_api",
        availability_status="available",
        tasks=["chat"],
        modalities=["text"],
    )

    response = client.get("/v1/models/org/detail-model")
    assert response.status_code == 200
    assert response.json()["display_name"] == "Detail Model"


def test_registry_pagination_is_bounded(client):
    response = client.get("/v1/models?limit=101")
    assert response.status_code == 422
