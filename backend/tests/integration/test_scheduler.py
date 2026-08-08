import asyncio
import os

import pytest
from sqlalchemy import text

from app.collectors.proxmox import ProxmoxSnapshot, snapshot_to_resources
from app.persistence.database import create_session_factory
from app.services.collector import CollectionSourceResult
from app.services.scheduler import ScheduledCollector, SourceDefinition


@pytest.mark.asyncio
async def test_scheduled_collector_isolates_source_timeout() -> None:
    async def fast_source() -> CollectionSourceResult:
        return CollectionSourceResult(
            source="proxmox",
            resources=snapshot_to_resources(ProxmoxSnapshot(node_name="scheduled-pve", node_status="online")),
        )

    async def slow_source() -> CollectionSourceResult:
        await asyncio.sleep(0.05)
        return CollectionSourceResult(source="docker", resources=[])

    factory = create_session_factory(os.environ["DATABASE_URL"])
    async with factory() as session:
        async with session.begin():
            result = await ScheduledCollector(session).run(
                [
                    SourceDefinition("proxmox", fast_source),
                    SourceDefinition("docker", slow_source),
                ],
                timeout_seconds=0.001,
                manage_transaction=False,
            )
            assert result.status == "partial"
            assert result.error_count == 1
            assert result.errors[0]["source"] == "docker"
            assert "timeout" in result.errors[0]["message"]
            await session.rollback()


@pytest.mark.asyncio
async def test_scheduled_collector_skips_when_advisory_lock_is_busy() -> None:
    factory = create_session_factory(os.environ["DATABASE_URL"])
    async with factory() as holder:
        async with holder.begin():
            lock = await holder.execute(
                text("SELECT pg_try_advisory_xact_lock(hashtext('homelab-monitor:collector'))")
            )
            assert lock.scalar_one() is True
            async with factory() as contender:
                async with contender.begin():
                    result = await ScheduledCollector(contender).run(
                        [], manage_transaction=False
                    )
                    assert result.status == "skipped"
                    assert result.errors == [
                        {"source": "scheduler", "message": "collector_lock_busy"}
                    ]
