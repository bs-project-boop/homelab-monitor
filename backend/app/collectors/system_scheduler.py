import hashlib
import re
from typing import Any

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")[:120] or "unknown"


def _cron_schedule(line: str) -> str:
    fields = line.split()
    if fields and fields[0].startswith("@"):
        return fields[0][:40]
    return " ".join(fields[:5])[:80] if len(fields) >= 5 else "unknown"


def _timer_job(group_id: str, fields: list[str]) -> Resource | None:
    if len(fields) < 2 or not fields[-2].endswith(".timer"):
        return None
    unit = fields[-2]
    service = fields[-1]
    disabled = fields[0] == "-" and fields[1] == "-"
    return Resource(
        id=f"{group_id}:job:systemd:{_slug(unit)}",
        kind=ResourceKind.CRON_JOB,
        name=unit,
        source="systemd",
        status=Status.MAINTENANCE if disabled else Status.UP,
        parent_id=group_id,
        metadata={"scheduler": "systemd", "unit": unit, "service": service, "next": fields[0][:80], "last": fields[3][:80] if len(fields) > 3 else "-"},
    )


def _cron_job(group_id: str, line: str, source: str, index: int) -> Resource:
    digest = hashlib.sha256(line.encode("utf-8", "replace")).hexdigest()[:12]
    return Resource(
        id=f"{group_id}:job:cron:{_slug(source)}:{digest}:{index}",
        kind=ResourceKind.CRON_JOB,
        name=f"{source} entry {index}",
        source="cron",
        status=Status.UP,
        parent_id=group_id,
        metadata={"scheduler": "cron", "schedule": _cron_schedule(line), "source_file": source[:240]},
    )


def scheduler_payload_to_resources(payload: dict[str, Any]) -> list[Resource]:
    target_id = str(payload["target_id"])
    timers_group = f"{target_id}:cron:systemd"
    cron_group = f"{target_id}:cron:cron"
    resources: list[Resource] = [
        Resource(id=timers_group, kind=ResourceKind.CRON_PROFILE, name=f"{payload['target_name']} systemd timers", source="systemd", status=Status.UP, parent_id=target_id, metadata={"scheduler": "systemd"}),
        Resource(id=cron_group, kind=ResourceKind.CRON_PROFILE, name=f"{payload['target_name']} cron", source="cron", status=Status.UP, parent_id=target_id, metadata={"scheduler": "cron"}),
    ]
    for raw_line in str(payload.get("timers", "")).splitlines():
        job = _timer_job(timers_group, raw_line.split())
        if job is not None:
            resources.append(job)
    cron_index = 0
    for raw_line in str(payload.get("crontab", "")).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("SHELL=") or line.startswith("PATH="):
            continue
        cron_index += 1
        resources.append(_cron_job(cron_group, line, "user-crontab", cron_index))
    for path in str(payload.get("cron_files", "")).splitlines():
        path = path.strip()
        if not path or path.endswith("/.placeholder"):
            continue
        cron_index += 1
        resources.append(_cron_job(cron_group, path, path, cron_index))
    resources[0].metadata["job_count"] = sum(resource.parent_id == timers_group and resource.kind == ResourceKind.CRON_JOB for resource in resources)
    resources[1].metadata["job_count"] = sum(resource.parent_id == cron_group and resource.kind == ResourceKind.CRON_JOB for resource in resources)
    return resources
