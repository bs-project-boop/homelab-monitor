import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.collectors.artifacts import automation_outputs_to_resources
from app.collectors.docker import load_ndjson, payloads_to_resources
from app.collectors.proxmox import load_json_fixture, payloads_to_snapshot, snapshot_to_resources
from app.collectors.hermes import profile_list_to_resources
from app.collectors.system_scheduler import scheduler_payload_to_resources
from app.services.collector import CollectionSourceResult


class CommandRunner(Protocol):
    async def run(self, args: Sequence[str]) -> str: ...


class SubprocessCommandRunner:
    async def run(self, args: Sequence[str]) -> str:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode().strip() or f"exit {process.returncode}"
            raise RuntimeError(message)
        return stdout.decode()


class ProxmoxPveshSource:
    def __init__(self, runner: CommandRunner, *, node_name: str) -> None:
        self.runner = runner
        self.node_name = node_name

    async def fetch(self) -> CollectionSourceResult:
        node = json.loads(await self.runner.run(["pvesh", "get", f"/nodes/{self.node_name}/status", "--output-format", "json"]))
        lxc = json.loads(await self.runner.run(["pvesh", "get", f"/nodes/{self.node_name}/lxc", "--output-format", "json"]))
        qemu = json.loads(await self.runner.run(["pvesh", "get", f"/nodes/{self.node_name}/qemu", "--output-format", "json"]))
        snapshot = payloads_to_snapshot(node_name=self.node_name, node_payload=node, lxc_payload=lxc, qemu_payload=qemu)
        return CollectionSourceResult(source="proxmox", resources=snapshot_to_resources(snapshot))


class DockerPctSource:
    def __init__(self, runner: CommandRunner, *, container_id: str) -> None:
        self.runner = runner
        self.container_id = container_id

    async def fetch(self) -> CollectionSourceResult:
        version = json.loads(await self.runner.run(["pct", "exec", self.container_id, "--", "docker", "version", "--format", "{{json .Server}}"]))
        output = await self.runner.run(["pct", "exec", self.container_id, "--", "docker", "ps", "-a", "--format", "{{json .}}"])
        containers = [json.loads(line) for line in output.splitlines() if line.strip()]
        return CollectionSourceResult(source="docker", resources=payloads_to_resources(container_id=self.container_id, version=version, containers=containers, include_workers=True))


@dataclass
class RelaySource:
    source: CollectionSourceResult

    async def fetch(self) -> CollectionSourceResult:
        return self.source


def docker_relay_sources(payload: object) -> list[RelaySource]:
    if not isinstance(payload, dict):
        raise ValueError("docker_relay_payload_must_be_object")
    sources: list[RelaySource] = []
    for container_id, raw in payload.items():
        if not isinstance(container_id, str) or not container_id.isdigit():
            raise ValueError("docker_relay_container_id_invalid")
        if not isinstance(raw, dict):
            raise ValueError("docker_relay_source_must_be_object")
        containers = raw.get("containers", [])
        if not isinstance(containers, list):
            raise ValueError("docker_relay_containers_must_be_array")
        version = raw.get("version", {})
        if not isinstance(version, dict):
            raise ValueError("docker_relay_version_must_be_object")
        sources.append(RelaySource(CollectionSourceResult(source=f"docker:{container_id}", resources=payloads_to_resources(container_id=container_id, version=version, containers=containers, include_workers=True))))
    return sources


class FixtureSource:
    def __init__(self, source: CollectionSourceResult) -> None:
        self.source = source

    async def fetch(self) -> CollectionSourceResult:
        return self.source


def fixture_sources(base: str | Path) -> list[FixtureSource]:
    root = Path(base)
    proxmox_base = root / "proxmox"
    docker_base = root / "docker"
    proxmox_snapshot = payloads_to_snapshot(node_name="pve", node_payload=load_json_fixture(proxmox_base / "node-status.json"), lxc_payload=load_json_fixture(proxmox_base / "lxc-list.json"), qemu_payload=load_json_fixture(proxmox_base / "qemu-list.json"))
    sources = [FixtureSource(CollectionSourceResult("proxmox", snapshot_to_resources(proxmox_snapshot)))]
    docker_resources = []
    for container_id in ("107", "110"):
        docker_resources.extend(payloads_to_resources(container_id=container_id, version=load_json_fixture(docker_base / f"ct{container_id}-docker-version.json"), containers=load_ndjson(docker_base / f"ct{container_id}-containers.ndjson")))
    sources.append(FixtureSource(CollectionSourceResult("docker", docker_resources)))
    return sources


@dataclass
class HermesRelaySource:
    payload: dict[str, object]

    async def fetch(self) -> CollectionSourceResult:
        hostname = self.payload.get("hostname")
        profile_output = self.payload.get("profiles_output")
        cron_outputs = self.payload.get("cron_outputs", {})
        cron_details = self.payload.get("cron_details", {})
        automation_outputs = self.payload.get("automation_outputs", [])
        cron_errors = self.payload.get("cron_errors", [])
        if not isinstance(hostname, str) or not hostname or len(hostname) > 255:
            raise ValueError("hermes_hostname_invalid")
        if not isinstance(profile_output, str) or len(profile_output) > 65536:
            raise ValueError("hermes_profile_output_invalid")
        if not isinstance(cron_outputs, dict) or any(not isinstance(k, str) or not isinstance(v, str) or len(v) > 65536 for k, v in cron_outputs.items()):
            raise ValueError("hermes_cron_outputs_invalid")
        if not isinstance(cron_details, dict) or len(json.dumps(cron_details, ensure_ascii=False)) > 262144:
            raise ValueError("hermes_cron_details_invalid")
        artifact_resources = automation_outputs_to_resources(automation_outputs)
        errors = [str(error)[:500] for error in cron_errors] if isinstance(cron_errors, list) else ["hermes_cron_errors_invalid"]
        resources = profile_list_to_resources(profile_output, hostname=hostname, cron_outputs=cron_outputs, cron_details=cron_details)
        return CollectionSourceResult(source="hermes", resources=[*resources, *artifact_resources], errors=errors)


def hermes_relay_sources(payload: object) -> list[HermesRelaySource]:
    if not isinstance(payload, dict):
        raise ValueError("hermes_relay_payload_must_be_object")
    return [HermesRelaySource(payload)]


@dataclass
class SchedulerRelaySource:
    payload: dict[str, object]

    async def fetch(self) -> CollectionSourceResult:
        required = ("target_id", "target_name", "timers", "crontab", "cron_files")
        if any(not isinstance(self.payload.get(key), str) for key in required):
            raise ValueError("scheduler_relay_payload_invalid")
        if any(len(str(self.payload.get(key, ""))) > 65536 for key in ("timers", "crontab", "cron_files")):
            raise ValueError("scheduler_relay_payload_too_large")
        errors = self.payload.get("errors", [])
        if not isinstance(errors, list):
            raise ValueError("scheduler_relay_errors_invalid")
        return CollectionSourceResult(source="system-scheduler", resources=scheduler_payload_to_resources(self.payload), errors=[str(error)[:300] for error in errors])


def scheduler_relay_sources(payload: object) -> list[SchedulerRelaySource]:
    if not isinstance(payload, dict):
        raise ValueError("scheduler_relay_payload_must_be_object")
    return [SchedulerRelaySource(payload)]
