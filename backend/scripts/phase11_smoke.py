from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
resources = client.get("/api/v1/resources").json()
latest = client.get("/api/v1/collector-runs/latest").json()
assert len(resources["data"]) == 29
assert resources["freshness"] == "fresh"
jellyseerr = next(item for item in resources["data"] if item["name"] == "jellyseerr")
assert jellyseerr["status"] == "degraded"
assert latest["data"]["status"] == "completed"
assert latest["data"]["resource_count"] == 29
assert latest["data"]["error_count"] == 0
print("API_RESOURCES=29")
print("JELLYSEERR_STATUS=" + jellyseerr["status"])
print("LATEST_RUN_STATUS=" + latest["data"]["status"])
