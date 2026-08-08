from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.resource import Resource
from app.repositories.collector_runs import CollectorRunRepository
from app.services.ingestion import IngestionService
from app.services.incidents import IncidentRepository
from app.repositories.logs import LogRepository
from app.services.logs import normalize_log


@dataclass(frozen=True)
class CollectionSourceResult:
    source: str
    resources: list[Resource]
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CollectorRunResult:
    run_id: str
    status: str
    resource_count: int
    error_count: int
    errors: list[dict[str, str]]


class CollectorOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.run_repository = CollectorRunRepository(session)
        self.ingestion = IngestionService(session)

    async def collect(self, sources: list[CollectionSourceResult]) -> CollectorRunResult:
        run_id = await self.run_repository.start()
        resources = [resource for source in sources for resource in source.resources]
        errors = [
            {"source": source.source, "message": message}
            for source in sources
            for message in source.errors
        ]
        await self.ingestion.ingest(resources, reason="collector_run")
        log_repository = LogRepository(self.session)
        for error in errors:
            await log_repository.append(normalize_log(
                resource_id=None,
                source=error["source"],
                level="error",
                message=error["message"],
                metadata={"collector_run_id": run_id},
            ))
        await IncidentRepository(self.session).reconcile(resources)
        status = "partial" if errors else "completed"
        await self.run_repository.complete(
            run_id,
            status=status,
            resource_count=len(resources),
            errors=errors,
        )
        return CollectorRunResult(
            run_id=run_id,
            status=status,
            resource_count=len(resources),
            error_count=len(errors),
            errors=errors,
        )
