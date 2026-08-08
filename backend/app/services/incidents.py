from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.resource import Resource
from app.domain.status import Status
from app.persistence.tables import incidents_table
from app.repositories.logs import LogRepository
from app.services.logs import normalize_log


@dataclass(frozen=True)
class IncidentCandidate:
    action: Literal["open", "resolve"]
    resource_id: str
    fingerprint: str
    severity: str
    title: str
    status: Status


def incident_candidate(resource: Resource) -> IncidentCandidate | None:
    if resource.status is Status.DEGRADED:
        return IncidentCandidate("open", resource.id, "availability", "warning", f"{resource.name} is degraded", resource.status)
    if resource.status is Status.DOWN:
        return IncidentCandidate("open", resource.id, "availability", "critical", f"{resource.name} is down", resource.status)
    if resource.status is Status.UP:
        return IncidentCandidate("resolve", resource.id, "availability", "info", f"{resource.name} recovered", resource.status)
    return None


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reconcile(self, resources: list[Resource]) -> int:
        changed = 0
        now = datetime.now(timezone.utc)
        for resource in resources:
            candidate = incident_candidate(resource)
            if candidate is None:
                continue
            existing = await self._get(candidate.resource_id, candidate.fingerprint)
            if candidate.action == "open":
                values = {
                    "resource_id": candidate.resource_id,
                    "fingerprint": candidate.fingerprint,
                    "status": "open",
                    "severity": candidate.severity,
                    "title": candidate.title,
                    "opened_at": existing["opened_at"] if existing else now,
                    "resolved_at": None,
                    "last_seen_at": now,
                    "metadata": {"observed_status": candidate.status.value},
                }
                statement = insert(incidents_table).values(id=f"incident:{candidate.resource_id}:{candidate.fingerprint}", **values)
                statement = statement.on_conflict_do_update(
                    constraint="uq_incidents_resource_fingerprint",
                    set_={key: statement.excluded[key] for key in values if key not in {"resource_id", "fingerprint", "opened_at"}},
                )
                await self.session.execute(statement)
                await LogRepository(self.session).append(
                    normalize_log(
                        resource_id=candidate.resource_id,
                        source=resource.source,
                        level=candidate.severity,
                        message=f"Incident opened: {candidate.title}",
                        metadata={"incident_id": f"incident:{candidate.resource_id}:{candidate.fingerprint}"},
                    ),
                    observed_at=existing["opened_at"] if existing else now,
                    fingerprint=f"incident:{candidate.resource_id}:{candidate.fingerprint}:opened",
                )
                changed += 1 if existing is None or existing["status"] != "open" else 0
            elif existing and existing["status"] == "open":
                await self.session.execute(
                    incidents_table.update()
                    .where(incidents_table.c.id == existing["id"])
                    .values(status="resolved", resolved_at=now, last_seen_at=now, title=candidate.title)
                )
                changed += 1
        return changed

    async def list(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        statement = select(incidents_table).order_by(incidents_table.c.last_seen_at.desc()).limit(limit)
        if status is not None:
            statement = statement.where(incidents_table.c.status == status)
        result = await self.session.execute(statement)
        return [dict(row) for row in result.mappings()]

    async def _get(self, resource_id: str, fingerprint: str) -> dict[str, object] | None:
        result = await self.session.execute(
            select(incidents_table).where(
                incidents_table.c.resource_id == resource_id,
                incidents_table.c.fingerprint == fingerprint,
            )
        )
        row = result.mappings().first()
        return dict(row) if row else None
