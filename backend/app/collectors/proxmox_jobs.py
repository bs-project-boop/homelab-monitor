import re
from typing import Any

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status

_ALLOWED_FIELDS = {
    "schedule": "schedule",
    "storage": "storage",
    "node": "node",
    "target": "target",
    "comment": "comment",
    "mode": "mode",
    "compress": "compress",
    "rate": "rate",
    "mailto": "mailto",
    "last_run": "last_run",
    "last_run_status": "last_run_status",
}


def _slug(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value))[:100] or "unknown"


def _enabled(item: dict[str, Any], *, disable_key: str) -> bool:
    if disable_key == "enabled" and "enabled" in item:
        return bool(item["enabled"])
    if disable_key in item:
        return not bool(item[disable_key])
    return not bool(item.get("disabled", False))


def _status(item: dict[str, Any], *, disable_key: str) -> Status:
    if not _enabled(item, disable_key=disable_key):
        return Status.MAINTENANCE
    if str(item.get("last_run_status", "")).lower() in {"error", "failed", "failure"}:
        return Status.DEGRADED
    return Status.UP


def _job_resource(group_id: str, kind: str, item: dict[str, Any]) -> Resource:
    job_id = _slug(item.get("id", item.get("name", "unknown")))
    metadata: dict[str, Any] = {"job_type": kind}
    if kind == "backup":
        metadata.update({
            "purpose_category": "backup_recovery",
            "purpose_title": "Workload backup",
            "purpose_summary": "Membuat recovery point untuk virtual machine atau container yang ditargetkan.",
            "impact_if_failed": "Tidak ada recovery point baru; pemulihan dapat bergantung pada backup yang lebih lama.",
            "purpose_confidence": "high",
        })
    elif kind == "replication":
        metadata.update({
            "purpose_category": "backup_recovery",
            "purpose_title": "Workload replication",
            "purpose_summary": "Menjaga salinan workload pada target replikasi untuk kebutuhan disaster recovery.",
            "impact_if_failed": "Salinan disaster recovery menjadi stale dan RPO dapat terlampaui.",
            "purpose_confidence": "high",
        })
    for input_key, output_key in _ALLOWED_FIELDS.items():
        if input_key in item and item[input_key] not in (None, ""):
            value = item[input_key]
            metadata[output_key] = str(value)[:300] if isinstance(value, str) else value
    name = str(item.get("comment") or item.get("name") or f"{kind} {job_id}")[:200]
    return Resource(
        id=f"{group_id}:job:{job_id}",
        kind=ResourceKind.CRON_JOB,
        name=name,
        source="proxmox",
        status=_status(item, disable_key="disable" if kind == "replication" else "enabled"),
        parent_id=group_id,
        metadata=metadata,
    )


def scheduled_jobs_to_resources(*, node_id: str, backups: list[dict[str, Any]], replications: list[dict[str, Any]]) -> list[Resource]:
    resources: list[Resource] = []
    for kind, items, disable_key in (("backup", backups, "enabled"), ("replication", replications, "disable")):
        group_id = f"{node_id}:cron:{kind}"
        resources.append(Resource(id=group_id, kind=ResourceKind.CRON_PROFILE, name=f"Proxmox {kind} jobs", source="proxmox", status=Status.UP, parent_id=node_id, metadata={"job_count": len(items), "job_type": kind}))
        resources.extend(_job_resource(group_id, kind, item) for item in items)
    return resources
