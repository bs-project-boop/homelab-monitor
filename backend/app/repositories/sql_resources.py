from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.resource import Resource
from app.domain.status import Status
from app.persistence.tables import resources_table, status_events_table


class ResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, resource: Resource) -> Resource:
        now = datetime.now(timezone.utc)
        values = {
            **resource.model_dump(mode="python"),
            "kind": resource.kind.value,
            "status": resource.status.value,
            "metadata": {**resource.metadata, "observed_at": now.isoformat()},
            "observed_at": now,
            "created_at": now,
            "updated_at": now,
        }
        statement = insert(resources_table).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[resources_table.c.id],
            set_={key: statement.excluded[key] for key in values if key not in {"id", "created_at"}},
        )
        await self.session.execute(statement)
        return resource

    async def get(self, resource_id: str) -> Resource | None:
        result = await self.session.execute(
            select(resources_table).where(resources_table.c.id == resource_id)
        )
        row = result.mappings().first()
        return self._to_resource(row) if row else None

    async def list(self) -> list[Resource]:
        result = await self.session.execute(
            select(resources_table).order_by(resources_table.c.name, resources_table.c.id)
        )
        return [self._to_resource(row) for row in result.mappings()]

    @staticmethod
    def _to_resource(row: Mapping[str, object]) -> Resource:
        values = dict(row)
        return Resource.model_validate(
            {key: values[key] for key in Resource.model_fields if key in values}
        )

    async def append_status_event(
        self,
        *,
        resource_id: str,
        previous_status: Status | None,
        status: Status,
        reason: str,
        metadata: dict[str, object] | None = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        statement = (
            insert(status_events_table)
            .values(
                resource_id=resource_id,
                previous_status=previous_status.value if previous_status else None,
                status=status.value,
                reason=reason,
                observed_at=now,
                metadata=metadata or {},
            )
            .returning(status_events_table.c.id)
        )
        event_id = (await self.session.execute(statement)).scalar_one()
        return int(event_id)

