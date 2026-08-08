import re
from typing import Any

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status

KNOWN_WORKERS = {"recyclarr", "unpackerr"}


def _label(labels: str, key: str) -> str | None:
    match = re.search(rf"(?:^|,){re.escape(key)}=([^,]+)", labels)
    return match.group(1) if match else None


def _container_status(state: str, status: str) -> Status:
    normalized_state = state.lower()
    normalized_status = status.lower()
    if "unhealthy" in normalized_status:
        return Status.DEGRADED
    if normalized_state == "running":
        return Status.UP
    if normalized_state in {"exited", "dead", "created"}:
        return Status.DOWN
    if normalized_state == "paused":
        return Status.DEGRADED
    return Status.UNKNOWN


def worker_resources(*, container_id: str, containers: list[dict[str, Any]]) -> list[Resource]:
    resources: list[Resource] = []
    for container in containers:
        labels = str(container.get("Labels", ""))
        service = _label(labels, "com.docker.compose.service")
        role = _label(labels, "com.beem.monitor.role")
        if service not in KNOWN_WORKERS and role != "worker":
            continue
        name = str(container.get("Names", "worker")).lstrip("/")
        parent_id = f"docker:{container_id}:container:{name}"
        metadata: dict[str, Any] = {
            "worker_type": "docker_worker",
            "compose_service": service or name,
            "image": str(container.get("Image", ""))[:240],
            "docker_state": str(container.get("State", "unknown"))[:40],
            "docker_status": str(container.get("Status", ""))[:240],
        }
        resources.append(Resource(
            id=f"{parent_id}:worker",
            kind=ResourceKind.CRON_JOB,
            name=f"{name} worker",
            source="docker",
            status=_container_status(str(container.get("State", "unknown")), str(container.get("Status", ""))),
            parent_id=parent_id,
            metadata=metadata,
        ))
    return resources
