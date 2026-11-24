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


def test_public_registry_is_empty_without_database_records(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_model_list_and_unreviewed_record_hidden(client):
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
        availability_status="review-required",
        tasks=["text-generation"],
        modalities=["text"],
    )

    response = client.get("/v1/models?q=Test")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["model_id"] == "alpha/test-chat"
    assert client.get("/v1/models/alpha/private-preview").status_code == 404


def test_model_detail_returns_available_model(client):
    insert_model(
        model_id="alpha/detail",
        display_name="Detail Model",
        provider="Alpha",
        availability_status="available",
        tasks=["chat"],
        modalities=["text"],
    )

    response = client.get("/v1/models/alpha/detail")
    assert response.status_code == 200
    assert response.json()["display_name"] == "Detail Model"


def test_registry_pagination_is_bounded(client):
    response = client.get("/v1/models?limit=101")
    assert response.status_code == 422
