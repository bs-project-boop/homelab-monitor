from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_collector_run_history_is_paginated_and_fresh() -> None:
    response = client.get("/api/v1/collector-runs?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["data"][0]["status"] == "completed"
    assert body["freshness"] == "fresh"
    assert body["partial_errors"] == []


def test_status_event_history_supports_resource_filter() -> None:
    response = client.get(
        "/api/v1/status-events",
        params={"resource_id": "docker:110:container:jellyseerr", "limit": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["freshness"] == "fresh"
    assert all(event["resource_id"] == "docker:110:container:jellyseerr" for event in body["data"])
    assert any(event["status"] == "degraded" for event in body["data"])


def test_history_limit_is_bounded() -> None:
    response = client.get("/api/v1/collector-runs?limit=101")
    assert response.status_code == 422
