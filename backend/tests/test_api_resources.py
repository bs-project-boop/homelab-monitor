from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_resources_contract_returns_data_and_freshness() -> None:
    response = client.get("/api/v1/resources")
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) >= 1
    assert body["source"] == "inventory"
    assert body["persistence"] == "postgresql"
    assert body["freshness"] == "fresh"


def test_unknown_resource_is_404() -> None:
    response = client.get("/api/v1/resources/missing:resource:1")
    assert response.status_code == 404

