from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_latest_collector_run_contract_is_empty_before_committed_run() -> None:
    response = client.get("/api/v1/collector-runs/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "completed"
    assert body["data"]["resource_count"] > 0
    assert body["data"]["error_count"] == 0
    assert body["persistence"] == "postgresql"
    assert body["freshness"] == "fresh"
