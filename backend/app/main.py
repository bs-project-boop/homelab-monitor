import os
from collections import Counter
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text

from app.domain.resource import Resource
from app.persistence.database import create_engine, create_session_factory
from app.repositories.collector_runs import CollectorRunRepository, StatusEventRepository
from app.repositories.logs import LogRepository
from app.repositories.sql_resources import ResourceRepository
from app.services.incidents import IncidentRepository
from app.services.versions import lookup_resources
from app.access import router as access_router

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://homelab_monitor@/homelab_monitor?host=/var/run/postgresql",
)
engine = create_engine(DATABASE_URL)
session_factory = create_session_factory(DATABASE_URL)

app = FastAPI(title="Homelab Monitor API", version="0.1.0")
app.include_router(access_router)


async def get_resource_repository() -> AsyncIterator[ResourceRepository]:
    async with session_factory() as session:
        yield ResourceRepository(session)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "up", "service": "monitor-api"}


@app.get("/api/v1/readiness")
async def readiness() -> dict[str, str]:
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database_not_ready") from exc
    return {"status": "ready", "database": "configured"}


@app.get("/api/v1/overview")
async def overview() -> dict[str, object]:
    async with session_factory() as session:
        resources = await ResourceRepository(session).list()
        latest_run = await CollectorRunRepository(session).latest()
    data = {
        "resource_count": len(resources),
        "status_counts": dict(Counter(resource.status.value for resource in resources)),
        "kind_counts": dict(Counter(resource.kind.value for resource in resources)),
        "source_counts": dict(Counter(resource.source for resource in resources)),
        "latest_collector_run": latest_run,
    }
    return {
        "data": data,
        "source": "overview",
        "persistence": "postgresql",
        "freshness": "fresh" if resources and latest_run else "empty",
        "partial_errors": latest_run.get("errors", []) if latest_run else [],
    }


@app.get("/api/v1/resources")
async def list_resources(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    resources = [resource.model_dump(mode="json") for resource in await repository.list()]
    return {
        "data": resources,
        "source": "inventory",
        "persistence": "postgresql",
        "freshness": "fresh" if resources else "empty",
        "partial_errors": [],
    }


@app.get("/api/v1/versions")
async def list_versions(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    resources = [resource.model_dump(mode="json") for resource in await repository.list()]
    data = await lookup_resources(resources)
    return {
        "data": data,
        "source": "docker-hub",
        "persistence": "memory-cache",
        "freshness": "fresh",
        "partial_errors": [],
    }


@app.get("/api/v1/automation-outputs")
async def list_automation_outputs(
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    async with session_factory() as session:
        resources = await ResourceRepository(session).list()
    artifacts_by_identity: dict[tuple[str, str], dict[str, object]] = {}
    for resource in resources:
        if resource.kind.value != "artifact":
            continue
        item = resource.model_dump(mode="json")
        metadata = item.get("metadata", {})
        identity = (str(item.get("name", "")), str(metadata.get("artifact_sha256", item.get("id", ""))))
        previous = artifacts_by_identity.get(identity)
        if previous is None or str(metadata.get("observed_at", "")) > str(previous.get("metadata", {}).get("observed_at", "")):
            artifacts_by_identity[identity] = item
    artifacts = list(artifacts_by_identity.values())
    artifacts.sort(key=lambda item: str(item.get("metadata", {}).get("generated_at", "")), reverse=True)
    return {
        "data": artifacts[:limit],
        "source": "automation-delivery",
        "persistence": "postgresql",
        "freshness": "fresh" if artifacts else "empty",
        "partial_errors": [],
    }


@app.get("/api/v1/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> Resource:
    resource = await repository.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource_not_found")
    return resource


@app.get("/api/v1/collector-runs/latest")
async def latest_collector_run() -> dict[str, object]:
    async with session_factory() as session:
        run = await CollectorRunRepository(session).latest()
    return {
        "data": run,
        "source": "collector",
        "persistence": "postgresql",
        "freshness": "fresh" if run else "empty",
        "partial_errors": run.get("errors", []) if run else [],
    }


@app.get("/api/v1/collector-runs")
async def list_collector_runs(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, object]:
    async with session_factory() as session:
        runs = await CollectorRunRepository(session).list(limit=limit)
    return {
        "data": runs,
        "source": "collector",
        "persistence": "postgresql",
        "freshness": "fresh" if runs else "empty",
        "partial_errors": [],
    }


@app.get("/api/v1/status-events")
async def list_status_events(
    resource_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    async with session_factory() as session:
        events = await StatusEventRepository(session).list(
            resource_id=resource_id, limit=limit
        )
    return {
        "data": events,
        "source": "status-events",
        "persistence": "postgresql",
        "freshness": "fresh" if events else "empty",
        "partial_errors": [],
    }


@app.get("/api/v1/incidents")
async def list_incidents(
    status: str | None = Query(default=None, pattern="^(open|resolved)$"),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    async with session_factory() as session:
        incidents = await IncidentRepository(session).list(status=status, limit=limit)
    return {
        "data": incidents,
        "source": "incidents",
        "persistence": "postgresql",
        "freshness": "fresh" if incidents else "empty",
        "partial_errors": [],
    }


@app.get("/api/v1/logs")
async def list_logs(
    resource_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    async with session_factory() as session:
        logs = await LogRepository(session).list(resource_id=resource_id, limit=limit)
    return {
        "data": logs,
        "source": "logs",
        "persistence": "postgresql",
        "freshness": "fresh" if logs else "empty",
        "partial_errors": [],
    }
