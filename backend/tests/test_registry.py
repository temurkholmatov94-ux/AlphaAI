from app.database import SessionLocal
from app.models import ModelRecord


def seed_records():
    db = SessionLocal()
    try:
        db.add_all(
            [
                ModelRecord(
                    model_id="alpha/test-chat",
                    display_name="Test Chat",
                    provider="Alpha",
                    license_status="verified",
                    access_method="hosted_api",
                    availability_status="available",
                    tasks=["text-generation"],
                    modalities=["text"],
                    weights_available=False,
                ),
                ModelRecord(
                    model_id="alpha/private-preview",
                    display_name="Private Preview",
                    provider="Alpha",
                    availability_status="review-required",
                    tasks=["text-generation"],
                    modalities=["text"],
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def test_public_registry_is_empty_without_database_records(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_model_list_and_private_record_hidden(client):
    from app.database import get_db
    from app.models import ModelRecord

    def seed_override():
        db = next(app.dependency_overrides[get_db]())
        try:
            db.add_all([
                ModelRecord(
                    model_id="alpha/test-chat",
                    display_name="Test Chat",
                    provider="Alpha",
                    license_status="verified",
                    access_method="hosted_api",
                    availability_status="available",
                    tasks=["text-generation"],
                    modalities=["text"],
                ),
                ModelRecord(
                    model_id="alpha/private-preview",
                    display_name="Private Preview",
                    provider="Alpha",
                    availability_status="review-required",
                    tasks=["text-generation"],
                    modalities=["text"],
                ),
            ])
            db.commit()
        finally:
            db.close()

    seed_override()
    response = client.get("/v1/models?q=Test")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["model_id"] == "alpha/test-chat"
    assert client.get("/v1/models/alpha/private-preview").status_code == 404


def test_model_detail_returns_available_model(client):
    from app.database import get_db
    from app.models import ModelRecord
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    try:
        db.add(ModelRecord(
            model_id="alpha/detail",
            display_name="Detail Model",
            provider="Alpha",
            availability_status="available",
            tasks=["chat"],
            modalities=["text"],
        ))
        db.commit()
    finally:
        db.close()

    response = client.get("/v1/models/alpha/detail")
    assert response.status_code == 200
    assert response.json()["display_name"] == "Detail Model"
