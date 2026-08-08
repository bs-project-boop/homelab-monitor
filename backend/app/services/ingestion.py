from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.resource import Resource
from app.repositories.sql_resources import ResourceRepository
from app.services.logs import normalize_log
from app.repositories.logs import LogRepository


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ResourceRepository(session)
        self.log_repository = LogRepository(session)

    async def ingest(self, resources: Iterable[Resource], *, reason: str) -> int:
        changed = 0
        for resource in resources:
            previous = await self.repository.get(resource.id)
            await self.repository.upsert(resource)
            if previous is None or previous.status != resource.status:
                await self.repository.append_status_event(
                    resource_id=resource.id,
                    previous_status=previous.status if previous else None,
                    status=resource.status,
                    reason=reason,
                    metadata={"source": resource.source},
                )
                await self.log_repository.append(normalize_log(
                    resource_id=resource.id,
                    source=resource.source,
                    level="error" if resource.status.value == "down" else "warning" if resource.status.value == "degraded" else "info",
                    message=f"{resource.name} observed {resource.status.value} during {reason}",
                    metadata={"previous_status": previous.status.value if previous else None, "reason": reason},
                ))
                changed += 1
        return changed
