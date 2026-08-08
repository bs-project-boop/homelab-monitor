import json

import pytest

from app.services.transport import DockerPctSource, ProxmoxPveshSource


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    async def run(self, args: list[str]) -> str:
        key = tuple(args)
        self.calls.append(key)
        return self.responses[key]


@pytest.mark.asyncio
async def test_proxmox_transport_uses_read_only_pvesh_commands() -> None:
    runner = FakeRunner(
        {
            ("pvesh", "get", "/nodes/pve/status", "--output-format", "json"): json.dumps({"pveversion": "test"}),
            ("pvesh", "get", "/nodes/pve/lxc", "--output-format", "json"): json.dumps([]),
            ("pvesh", "get", "/nodes/pve/qemu", "--output-format", "json"): json.dumps([]),
        }
    )
    result = await ProxmoxPveshSource(runner, node_name="pve").fetch()
    assert result.source == "proxmox"
    assert len(result.resources) == 1
    assert all(call[0] == "pvesh" for call in runner.calls)


@pytest.mark.asyncio
async def test_docker_transport_uses_read_only_pct_docker_commands() -> None:
    runner = FakeRunner(
        {
            ("pct", "exec", "107", "--", "docker", "version", "--format", "{{json .Server}}"): json.dumps({"Version": "test"}),
            ("pct", "exec", "107", "--", "docker", "ps", "-a", "--format", "{{json .}}"): json.dumps({"ID": "abc", "Names": "fixture", "Image": "fixture", "State": "running", "Status": "Up"}),
        }
    )
    result = await DockerPctSource(runner, container_id="107").fetch()
    assert result.source == "docker"
    assert [resource.name for resource in result.resources] == ["docker-ct-107", "fixture"]
    assert all(call[:3] == ("pct", "exec", "107") for call in runner.calls)
