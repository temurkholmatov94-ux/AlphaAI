from datetime import datetime, timezone
from types import SimpleNamespace

from app.database import get_db
from app.discovery.huggingface import HuggingFaceDiscovery, map_huggingface_model
from app.main import app
from app.models import ModelRecord


def test_huggingface_mapping_never_approves_model_automatically():
    info = SimpleNamespace(
        id="example-org/example-model",
        card_data=SimpleNamespace(license="apache-2.0"),
        pipeline_tag="text-generation",
        last_modified=datetime(2026, 1, 1, tzinfo=timezone.utc),
        gated=False,
        downloads=1200,
        likes=42,
        library_name="transformers",
        sha="abc123",
        siblings=[SimpleNamespace(rfilename="config.json"), SimpleNamespace(rfilename="model.safetensors")],
    )
    mapped = map_huggingface_model(info)
    assert mapped["model_id"] == "example-org/example-model"
    assert mapped["license_id"] == "apache-2.0"
    assert mapped["license_status"] == "unknown"
    assert mapped["availability_status"] == "review-required"
    assert mapped["weights_available"] is True
    assert mapped["weights_status"] == "public"


def test_discovery_records_are_not_public(client):
    info = SimpleNamespace(
        id="example-org/not-yet-reviewed",
        card_data=SimpleNamespace(license="mit"),
        pipeline_tag="text-generation",
        last_modified=None,
        gated=False,
        downloads=5,
        likes=1,
        library_name="transformers",
        sha="rev123",
    )
    mapped = map_huggingface_model(info)
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(ModelRecord(**mapped))
        db.commit()
    finally:
        db.close()
        db_generator.close()

    assert client.get("/v1/models/example-org/not-yet-reviewed").status_code == 404


def test_discovery_upsert_preserves_human_review_decisions(client):
    info = SimpleNamespace(
        id="example-org/approved-model",
        card_data=SimpleNamespace(license="apache-2.0"),
        pipeline_tag="text-generation",
        last_modified=datetime(2026, 2, 1, tzinfo=timezone.utc),
        gated=False,
        downloads=99,
        likes=8,
        library_name="transformers",
        sha="newrevision",
    )

    class FakeAPI:
        def list_models(self, **kwargs):
            assert kwargs["limit"] == 10
            assert kwargs["search"] == "approved"
            return [info]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(ModelRecord(
            model_id="example-org/approved-model",
            display_name="Approved Model",
            provider="Hugging Face",
            license_status="verified",
            access_method="hosted_api",
            availability_status="available",
            tasks=["text-generation"],
            modalities=["text"],
        ))
        db.commit()

        result = HuggingFaceDiscovery(api=FakeAPI()).ingest(
            db, limit=10, search="approved"
        )
        record = db.query(ModelRecord).filter_by(
            model_id="example-org/approved-model"
        ).one()
        assert result == {"fetched": 1, "created": 0, "updated": 1}
        assert record.license_status == "verified"
        assert record.availability_status == "available"
        assert record.access_method == "hosted_api"
        assert record.upstream_revision == "newrevision"
    finally:
        db.close()
        db_generator.close()



def test_discovery_distinguishes_gated_missing_and_unknown_weights():
    gated = SimpleNamespace(
        id="example-org/gated-model",
        card_data=None,
        gated=True,
        siblings=[SimpleNamespace(rfilename="model.safetensors")],
    )
    missing = SimpleNamespace(
        id="example-org/no-weight-files",
        card_data=None,
        gated=False,
        siblings=[SimpleNamespace(rfilename="config.json")],
    )
    unknown = SimpleNamespace(id="example-org/partial-metadata", card_data=None)

    assert map_huggingface_model(gated)["weights_status"] == "gated"
    assert map_huggingface_model(gated)["weights_available"] is False
    assert map_huggingface_model(missing)["weights_status"] == "not_listed"
    assert map_huggingface_model(missing)["weights_available"] is False
    assert map_huggingface_model(unknown)["weights_status"] == "unknown"
    assert map_huggingface_model(unknown)["weights_available"] is False


def test_discovery_refreshes_weight_facts_without_changing_human_publication():
    info = SimpleNamespace(
        id="example-org/approved-model",
        card_data=SimpleNamespace(license="apache-2.0"),
        pipeline_tag="text-generation",
        last_modified=None,
        gated=False,
        downloads=99,
        likes=8,
        library_name="transformers",
        sha="newrevision",
        siblings=[SimpleNamespace(rfilename="model.safetensors")],
    )

    class FakeAPI:
        def list_models(self, **kwargs):
            assert kwargs["full"] is True
            return [info]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(ModelRecord(
            model_id="example-org/approved-model",
            display_name="Approved Model",
            provider="Hugging Face",
            license_status="verified",
            access_method="download",
            availability_status="available",
            tasks=["text-generation"],
            modalities=["text"],
            weights_status="unknown",
        ))
        db.commit()
        HuggingFaceDiscovery(api=FakeAPI()).ingest(db, limit=10)
        record = db.query(ModelRecord).filter_by(model_id="example-org/approved-model").one()
        assert record.weights_available is True
        assert record.weights_status == "public"
        assert record.availability_status == "available"
        assert record.license_status == "verified"
    finally:
        db.close()
        db_generator.close()
