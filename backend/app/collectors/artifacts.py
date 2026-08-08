from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


def automation_outputs_to_resources(payload: object) -> list[Resource]:
    if not isinstance(payload, list):
        raise ValueError("automation_outputs_must_be_array")
    resources: list[Resource] = []
    for raw in payload[:200]:
        if not isinstance(raw, dict):
            raise ValueError("automation_output_must_be_object")
        output_id = raw.get("id")
        name = raw.get("artifact_name")
        observed_at = raw.get("observed_at")
        if not all(isinstance(value, str) and value for value in (output_id, name, observed_at)):
            raise ValueError("automation_output_identity_invalid")
        metadata = {key: value for key, value in raw.items() if key not in {"id", "artifact_name"}}
        metadata["observed_at"] = observed_at
        resources.append(
            Resource(
                id=output_id,
                kind=ResourceKind.ARTIFACT,
                name=name,
                source="automation-delivery",
                status=artifact_status(metadata),
                metadata=metadata,
            )
        )
    return resources


def artifact_status(metadata: dict[str, Any]) -> Status:
    artifact_state = metadata.get("artifact_status")
    if artifact_state not in {"generated", "not_observed"}:
        return Status.UNKNOWN
    if artifact_state == "not_observed":
        return Status.UNKNOWN
    github = str((metadata.get("github") or {}).get("status", "unknown"))
    discord = str((metadata.get("discord") or {}).get("status", "unknown"))
    if "failed" in {github, discord}:
        return Status.DEGRADED
    return Status.UP


def observed_now() -> str:
    return datetime.now(timezone.utc).isoformat()
