from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "up", "service": "monitor-api"}


def test_readiness_contract() -> None:
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
