from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.tables import collector_runs_table, status_events_table


class CollectorRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start(self) -> str:
        run_id = str(uuid4())
        await self.session.execute(
            collector_runs_table.insert().values(
                id=run_id,
                status="running",
                started_at=datetime.now(timezone.utc),
                resource_count=0,
                error_count=0,
                errors=[],
            )
        )
        return run_id

    async def complete(
        self,
        run_id: str,
        *,
        status: str,
        resource_count: int,
        errors: list[dict[str, str]],
    ) -> None:
        await self.session.execute(
            collector_runs_table.update()
            .where(collector_runs_table.c.id == run_id)
            .values(
                status=status,
                completed_at=datetime.now(timezone.utc),
                resource_count=resource_count,
                error_count=len(errors),
                errors=errors,
            )
        )

    async def latest(self) -> dict[str, object] | None:
        rows = await self.list(limit=1)
        return rows[0] if rows else None

    async def list(self, *, limit: int = 50) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(collector_runs_table)
            .order_by(collector_runs_table.c.started_at.desc())
            .limit(limit)
        )
        return [dict(row) for row in result.mappings()]


class StatusEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, *, resource_id: str | None = None, limit: int = 100
    ) -> list[dict[str, object]]:
        statement = select(status_events_table).order_by(
            status_events_table.c.observed_at.desc(), status_events_table.c.id.desc()
        )
        if resource_id is not None:
            statement = statement.where(status_events_table.c.resource_id == resource_id)
        result = await self.session.execute(statement.limit(limit))
        return [dict(row) for row in result.mappings()]
