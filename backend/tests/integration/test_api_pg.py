from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_readiness_reports_database_configured() -> None:
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    assert response.json()["database"] == "configured"


def test_resources_contract_is_database_backed() -> None:
    response = client.get("/api/v1/resources")
    assert response.status_code == 200
    assert response.json()["persistence"] == "postgresql"
