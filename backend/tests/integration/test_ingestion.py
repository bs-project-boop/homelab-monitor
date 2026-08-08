from app.collectors.proxmox import ProxmoxGuestSnapshot, ProxmoxSnapshot, snapshot_to_resources
from app.persistence.database import create_session_factory
from app.persistence.tables import status_events_table
from app.services.ingestion import IngestionService

import os
import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_ingestion_upserts_resources_and_events_then_rolls_back() -> None:
    snapshot = ProxmoxSnapshot(
        node_name="test-pve",
        node_status="online",
        guests=[ProxmoxGuestSnapshot(vmid=998, kind="lxc", name="fixture", status="running")],
    )
    resources = snapshot_to_resources(snapshot)
    factory = create_session_factory(os.environ["DATABASE_URL"])

    async with factory() as session:
        async with session.begin():
            nested = await session.begin_nested()
            service = IngestionService(session)
            await service.ingest(resources, reason="proxmox_fixture")
            stored = await service.repository.get("proxmox:lxc:998")
            assert stored is not None
            assert stored.status.value == "up"
            events = await session.execute(
                select(status_events_table).where(
                    status_events_table.c.resource_id == "proxmox:lxc:998"
                )
            )
            assert len(events.fetchall()) == 1
            await nested.rollback()

    async with factory() as session:
        assert await IngestionService(session).repository.get("proxmox:lxc:998") is None
