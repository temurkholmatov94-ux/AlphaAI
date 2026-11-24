from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "alphaai-control-plane",
    }


def test_readiness_checks_database(client) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "alphaai-control-plane",
    }


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "The Intelligence Universe" in response.text
    assert "Not a live inference service" in response.text


def test_model_explorer_page_is_served() -> None:
    response = client.get("/models")
    assert response.status_code == 200
    assert "Find the right model." in response.text
    assert "/v1/models" in response.text


def test_managed_postgres_url_uses_psycopg3_driver() -> None:
    from app.database import build_engine

    engine = build_engine("postgresql://alpha:secret@example.test:5432/alpha")
    try:
        assert engine.url.drivername == "postgresql+psycopg"
    finally:
        engine.dispose()
