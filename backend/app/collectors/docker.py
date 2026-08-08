import json
import re
from pathlib import Path
from typing import Any

from app.collectors.docker_workers import worker_resources
from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


def load_ndjson(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


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


def _label(labels: str, key: str) -> str | None:
    match = re.search(rf"(?:^|,){re.escape(key)}=([^,]+)", labels)
    return match.group(1) if match else None


def _safe_metadata(container: dict[str, Any]) -> dict[str, Any]:
    labels = str(container.get("Labels", ""))
    metadata: dict[str, Any] = {
        "container_id": container.get("ID"),
        "image": container.get("Image"),
        "docker_state": container.get("State"),
        "docker_status": container.get("Status"),
        "ports": container.get("Ports"),
        "networks": container.get("Networks"),
    }
    for field, key in {
        "compose_project": "com.docker.compose.project",
        "compose_service": "com.docker.compose.service",
        "compose_working_dir": "com.docker.compose.project.working_dir",
    }.items():
        value = _label(labels, key)
        if value is not None:
            metadata[field] = value
    return {key: value for key, value in metadata.items() if value not in (None, "")}


def payloads_to_resources(
    *, container_id: str, version: dict[str, Any], containers: list[dict[str, Any]], include_workers: bool = False
) -> list[Resource]:
    host_id = f"docker:host:{container_id}"
    resources = [
        Resource(
            id=host_id,
            kind=ResourceKind.DOCKER_HOST,
            name=f"docker-ct-{container_id}",
            source="docker",
            status=Status.UP,
            parent_id=f"proxmox:lxc:{container_id}",
            metadata={"docker_version": version.get("Version"), "api_version": version.get("ApiVersion")},
        )
    ]
    for container in containers:
        name = str(container["Names"]).lstrip("/")
        resources.append(
            Resource(
                id=f"docker:{container_id}:container:{name}",
                kind=ResourceKind.CONTAINER,
                name=name,
                source="docker",
                status=_container_status(str(container.get("State", "unknown")), str(container.get("Status", ""))),
                parent_id=host_id,
                metadata=_safe_metadata(container),
            )
        )
    if include_workers:
        resources.extend(worker_resources(container_id=container_id, containers=containers))
    return resources
