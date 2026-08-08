import asyncio
import json
import os
from pathlib import Path

from app.collectors.docker import load_ndjson, payloads_to_resources
from app.collectors.proxmox import load_json_fixture, payloads_to_snapshot, snapshot_to_resources
from app.persistence.database import create_session_factory
from app.services.collector import CollectionSourceResult, CollectorOrchestrator


async def main() -> None:
    proxmox_base = Path("/opt/homelab-monitor/docs/fixtures/proxmox")
    docker_base = Path("/opt/homelab-monitor/docs/fixtures/docker")
    proxmox_snapshot = payloads_to_snapshot(
        node_name="pve",
        node_payload=load_json_fixture(proxmox_base / "node-status.json"),
        lxc_payload=load_json_fixture(proxmox_base / "lxc-list.json"),
        qemu_payload=load_json_fixture(proxmox_base / "qemu-list.json"),
    )
    docker_resources = []
    for container_id in ("107", "110"):
        docker_resources.extend(
            payloads_to_resources(
                container_id=container_id,
                version=load_json_fixture(docker_base / f"ct{container_id}-docker-version.json"),
                containers=load_ndjson(docker_base / f"ct{container_id}-containers.ndjson"),
            )
        )
    sources = [
        CollectionSourceResult(source="proxmox", resources=snapshot_to_resources(proxmox_snapshot)),
        CollectionSourceResult(source="docker", resources=docker_resources),
    ]
    factory = create_session_factory(os.environ["DATABASE_URL"])
    async with factory() as session:
        async with session.begin():
            result = await CollectorOrchestrator(session).collect(sources)
    print(json.dumps(result.__dict__, sort_keys=True))


asyncio.run(main())
