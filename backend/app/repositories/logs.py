from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.tables import logs_table
from app.services.logs import NormalizedLog


class LogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, log: NormalizedLog, *, observed_at: datetime | None = None, fingerprint: str | None = None) -> str:
        observed = observed_at or datetime.now(timezone.utc)
        key = fingerprint or hashlib.sha256(
            f"{log.resource_id}|{log.source}|{log.level}|{log.message}|{observed.isoformat()}".encode()
        ).hexdigest()
        log_id = f"log:{key}"
        statement = insert(logs_table).values(
            id=log_id,
            resource_id=log.resource_id,
            source=log.source,
            level=log.level,
            message=log.message,
            fingerprint=key,
            observed_at=observed,
            metadata=log.metadata,
        ).on_conflict_do_nothing(index_elements=[logs_table.c.fingerprint])
        await self.session.execute(statement)
        return log_id

    async def list(self, *, resource_id: str | None = None, incident_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        statement = select(logs_table).order_by(logs_table.c.observed_at.desc()).limit(limit)
        if resource_id:
            statement = statement.where(logs_table.c.resource_id == resource_id)
        result = await self.session.execute(statement)
        return [self._serialize(row) for row in result.mappings()]

    @staticmethod
    def _serialize(row: Mapping[str, object]) -> dict[str, Any]:
        return dict(row)
