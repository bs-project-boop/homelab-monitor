import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.collector import CollectionSourceResult, CollectorOrchestrator, CollectorRunResult


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    fetch: Callable[[], Awaitable[CollectionSourceResult]]


class ScheduledCollector:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(
        self,
        sources: list[SourceDefinition],
        *,
        timeout_seconds: float = 30.0,
        manage_transaction: bool = True,
    ) -> CollectorRunResult:
        if manage_transaction:
            async with self.session.begin():
                return await self._run(sources, timeout_seconds)
        return await self._run(sources, timeout_seconds)

    async def _run(
        self, sources: list[SourceDefinition], timeout_seconds: float
    ) -> CollectorRunResult:
        lock_result = await self.session.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtext('homelab-monitor:collector'))")
        )
        if not lock_result.scalar_one():
            return CollectorRunResult(
                run_id="",
                status="skipped",
                resource_count=0,
                error_count=1,
                errors=[{"source": "scheduler", "message": "collector_lock_busy"}],
            )

        async def fetch_source(source: SourceDefinition) -> CollectionSourceResult:
            try:
                return await asyncio.wait_for(source.fetch(), timeout=timeout_seconds)
            except TimeoutError:
                return CollectionSourceResult(source=source.name, resources=[], errors=[f"timeout after {timeout_seconds:g}s"])
            except Exception as exc:
                return CollectionSourceResult(source=source.name, resources=[], errors=[f"source failure: {type(exc).__name__}"])

        results = list(await asyncio.gather(*(fetch_source(source) for source in sources)))
        return await CollectorOrchestrator(self.session).collect(results)
