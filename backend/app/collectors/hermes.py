import re
from dataclasses import dataclass
from typing import Any

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


@dataclass(frozen=True)
class HermesProfileSnapshot:
    name: str
    model: str
    gateway: str
    alias: str
    distribution: str
    active: bool


@dataclass(frozen=True)
class HermesCronJobSnapshot:
    job_id: str
    state: str
    name: str
    metadata: dict[str, str]


def parse_profile_list(output: str) -> list[HermesProfileSnapshot]:
    profiles: list[HermesProfileSnapshot] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Profile") or set(line) <= {"─", "-", " "}:
            continue
        active = line.startswith("◆")
        line = line.lstrip(" ◆")
        gateway_match = re.search(r"\s{2,}(?P<gateway>running|stopped|degraded|down|unknown)(?:\s{2,}|$)", line)
        if not gateway_match:
            continue
        prefix = line[:gateway_match.start()].strip()
        prefix_fields = prefix.split()
        if len(prefix_fields) < 2:
            continue
        name, model = prefix_fields[0], prefix_fields[-1]
        suffix = line[gateway_match.end():].strip()
        suffix_fields = re.split(r"\s{2,}", suffix) if suffix else []
        profiles.append(HermesProfileSnapshot(name, model, gateway_match.group("gateway"), suffix_fields[0] if suffix_fields else "—", suffix_fields[1] if len(suffix_fields) > 1 else "—", active))
    return profiles


def parse_cron_list(output: str) -> list[HermesCronJobSnapshot]:
    jobs: list[HermesCronJobSnapshot] = []
    current_id = current_state = None
    fields: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_id, current_state, fields
        if current_id is not None:
            jobs.append(HermesCronJobSnapshot(current_id, current_state or "unknown", fields.get("Name", current_id), dict(fields)))
        current_id, current_state, fields = None, None, {}

    for raw_line in output.splitlines():
        header = re.match(r"^\s{2}([A-Za-z0-9_-]{6,64})\s+\[([A-Za-z0-9_-]+)\]\s*$", raw_line)
        if header:
            flush()
            current_id, current_state = header.group(1), header.group(2).lower()
            continue
        if current_id is None:
            continue
        field = re.match(r"^\s{4}([A-Za-z][A-Za-z ]+):\s*(.*?)\s*$", raw_line)
        if field:
            key, value = field.group(1).strip(), field.group(2).strip()
            fields[key] = value[:500]
    flush()
    return jobs


def _cron_status(job: HermesCronJobSnapshot) -> Status:
    last_run = job.metadata.get("Last run", "").lower()
    if job.state == "paused":
        return Status.MAINTENANCE
    if re.search(r"\b(error|failed|failure)\b", last_run):
        return Status.DEGRADED
    if job.state == "active":
        return Status.UP
    return Status.UNKNOWN


def profile_list_to_resources(output: str, *, hostname: str, cron_outputs: dict[str, str] | None = None, cron_details: dict[str, dict[str, dict[str, object]]] | None = None) -> list[Resource]:
    profiles = parse_profile_list(output)
    has_cron_snapshot = cron_outputs is not None
    cron_outputs = cron_outputs or {}
    cron_details = cron_details or {}
    host_id = f"hermes:host:{hostname}"
    host_metadata: dict[str, Any] = {"profile_count": len(profiles)}
    resources = [Resource(id=host_id, kind=ResourceKind.HERMES_HOST, name=hostname, source="hermes", status=Status.UP if any(p.gateway == "running" for p in profiles) else Status.UNKNOWN, metadata=host_metadata)]
    for profile in profiles:
        profile_id = f"hermes:{hostname}:profile:{profile.name}"
        jobs = parse_cron_list(cron_outputs.get(profile.name, "")) if has_cron_snapshot else []
        profile_metadata: dict[str, Any] = {"model": profile.model[:160], "gateway": profile.gateway[:40], "alias": profile.alias[:100], "distribution": profile.distribution[:100]}
        if has_cron_snapshot:
            profile_metadata["cron_job_count"] = len(jobs)
        resources.append(Resource(id=profile_id, kind=ResourceKind.HERMES_PROFILE, name=profile.name, source="hermes", status=Status.UP if profile.gateway == "running" else Status.UNKNOWN, parent_id=host_id, metadata=profile_metadata))
        if not has_cron_snapshot:
            continue
        cron_profile_id = f"{profile_id}:cron"
        resources.append(Resource(id=cron_profile_id, kind=ResourceKind.CRON_PROFILE, name=f"{profile.name} cron", source="hermes", status=Status.DEGRADED if any(_cron_status(j) == Status.DEGRADED for j in jobs) else Status.UP, parent_id=profile_id, metadata={"job_count": len(jobs)}))
        for job in jobs:
            metadata = {"state": job.state, "schedule": job.metadata.get("Schedule", "")[:120], "next_run": job.metadata.get("Next run", "")[:80], "deliver": job.metadata.get("Deliver", "")[:160], "last_run": job.metadata.get("Last run", "")[:160]}
            for key, out_key, limit in (("skills", "Skills", 300), ("workdir", "Workdir", 300), ("script", "Script", 300), ("mode", "Mode", 80)):
                if out_key in job.metadata:
                    metadata[key] = job.metadata[out_key][:limit]
            detail = cron_details.get(profile.name, {}).get(job.job_id, {})
            for key, limit in (("purpose", 1200), ("impact_if_failed", 900), ("execution_mode", 80), ("summary_source", 80), ("summary_generated_at", 80), ("prompt_hash", 128)):
                value = detail.get(key)
                if isinstance(value, str) and value.strip():
                    metadata[key] = value[:limit]
            scope = detail.get("scope")
            if isinstance(scope, list) and all(isinstance(item, str) for item in scope):
                metadata["scope"] = [item[:200] for item in scope[:20]]
            resources.append(Resource(id=f"{cron_profile_id}:job:{job.job_id}", kind=ResourceKind.CRON_JOB, name=job.name, source="hermes", status=_cron_status(job), parent_id=cron_profile_id, metadata=metadata))
    if has_cron_snapshot:
        resources[0].metadata["cron_job_count"] = sum(r.kind == ResourceKind.CRON_JOB for r in resources)
    return resources
