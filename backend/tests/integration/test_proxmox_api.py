import httpx
import pytest

from app.services.proxmox_api import ProxmoxApiSource


@pytest.mark.asyncio
async def test_proxmox_api_source_reads_read_only_state_and_schedule_endpoints() -> None:
    responses = {
        "/api2/json/nodes/pve/status": {"pveversion": "test"},
        "/api2/json/nodes/pve/lxc": [],
        "/api2/json/nodes/pve/qemu": [],
        "/api2/json/cluster/backup": [{"id": "backup-1", "enabled": 1}],
        "/api2/json/cluster/replication": [{"id": "replication-1", "disable": 1}],
    }
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": responses[request.url.path]})

    source = ProxmoxApiSource(
        base_url="https://pve.test:8006",
        token="monitor@pve!collector=test-token",
        ca_cert="/unused-in-mock-test.pem",
        node_name="pve",
        transport=httpx.MockTransport(handler),
    )
    result = await source.fetch()
    assert result.source == "proxmox"
    assert len(result.resources) == 5
    assert [request.url.path for request in seen] == list(responses)
    assert all(request.headers["authorization"].startswith("PVEAPIToken=") for request in seen)
