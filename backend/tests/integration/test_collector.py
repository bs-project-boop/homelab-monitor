import os

import pytest

from app.collectors.docker import payloads_to_resources
from app.collectors.proxmox import ProxmoxGuestSnapshot, ProxmoxSnapshot, snapshot_to_resources
from app.persistence.database import create_session_factory
from app.services.collector import CollectionSourceResult, CollectorOrchestrator


@pytest.mark.asyncio
async def test_combined_collector_records_partial_run_and_ingests_resources() -> None:
    sources = [
        CollectionSourceResult(
            source="proxmox",
            resources=snapshot_to_resources(
                ProxmoxSnapshot(
                    node_name="run-pve",
                    node_status="online",
                    guests=[ProxmoxGuestSnapshot(vmid=998, kind="lxc", name="fixture", status="running")],
                )
            ),
        ),
        CollectionSourceResult(
            source="docker",
            resources=payloads_to_resources(
                container_id="998",
                version={"Version": "test"},
                containers=[
                    {"ID": "abc", "Names": "fixture", "Image": "fixture:latest", "State": "running", "Status": "Up"}
                ],
            ),
            errors=["docker health endpoint unavailable"],
        ),
    ]

    factory = create_session_factory(os.environ["DATABASE_URL"])
    async with factory() as session:
        async with session.begin():
            nested = await session.begin_nested()
            result = await CollectorOrchestrator(session).collect(sources)
            assert result.status == "partial"
            assert result.resource_count == 4
            assert result.error_count == 1
            assert result.errors == [{"source": "docker", "message": "docker health endpoint unavailable"}]
            await nested.rollback()
