from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_overview_contract_contains_inventory_health_and_freshness() -> None:
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["resource_count"] >= 29
    assert body["data"]["status_counts"]["degraded"] >= 1
    assert body["data"]["source_counts"]["docker"] == 17
    assert body["data"]["source_counts"]["probe"] >= 9
    assert body["data"]["kind_counts"]["container"] == 13
    assert body["data"]["latest_collector_run"]["status"] == "completed"
    assert body["freshness"] == "fresh"
    assert body["partial_errors"] == []
