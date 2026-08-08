import asyncio
import time
from dataclasses import dataclass
from typing import Literal

import httpx

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status

Protocol = Literal["tcp", "http"]


@dataclass(frozen=True)
class ProbeTarget:
    id: str
    name: str
    host: str
    port: int
    protocol: Protocol
    parent_id: str | None = None
    path: str = "/"


@dataclass(frozen=True)
class ProbeObservation:
    success: bool
    latency_ms: float | None
    status_code: int | None = None
    error: str | None = None


def observation_to_resource(target: ProbeTarget, observation: ProbeObservation) -> Resource:
    status = Status.UP if observation.success else (
        Status.DEGRADED if observation.status_code is not None else Status.DOWN
    )
    metadata: dict[str, object] = {
        "protocol": target.protocol,
        "port": target.port,
    }
    if observation.latency_ms is not None:
        metadata["latency_ms"] = observation.latency_ms
    if observation.status_code is not None:
        metadata["status_code"] = observation.status_code
    if observation.error:
        metadata["error"] = observation.error[:160]
    return Resource(
        id=target.id,
        kind=ResourceKind.SERVICE,
        name=target.name,
        source="probe",
        status=status,
        parent_id=target.parent_id,
        address=f"{target.host}:{target.port}{target.path if target.protocol == 'http' else ''}",
        metadata=metadata,
    )


async def probe_tcp(target: ProbeTarget, *, timeout: float = 3.0) -> ProbeObservation:
    started = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target.host, target.port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return ProbeObservation(True, round((time.perf_counter() - started) * 1000, 2))
    except asyncio.TimeoutError:
        return ProbeObservation(False, None, error="connect_timeout")
    except OSError as exc:
        return ProbeObservation(False, None, error=f"connect_error:{exc.__class__.__name__}")


async def probe_http(target: ProbeTarget, *, timeout: float = 5.0) -> ProbeObservation:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(f"http://{target.host}:{target.port}{target.path}")
        latency = round((time.perf_counter() - started) * 1000, 2)
        if 200 <= response.status_code < 400:
            return ProbeObservation(True, latency, response.status_code)
        return ProbeObservation(False, latency, response.status_code, f"HTTP {response.status_code}")
    except httpx.TimeoutException:
        return ProbeObservation(False, None, error="http_timeout")
    except httpx.HTTPError as exc:
        return ProbeObservation(False, None, error=f"http_error:{exc.__class__.__name__}")


async def probe_target(target: ProbeTarget, *, timeout: float | None = None) -> Resource:
    observation = await (
        probe_http(target, timeout=timeout or 5.0)
        if target.protocol == "http"
        else probe_tcp(target, timeout=timeout or 3.0)
    )
    return observation_to_resource(target, observation)


def default_probe_targets() -> list[ProbeTarget]:
    targets = [
        ProbeTarget("probe:http:monitoring:18080", "monitoring frontend", "10.10.10.55", 18080, "http", "proxmox:lxc:112"),
        ProbeTarget("probe:tcp:monitoring:5432", "monitoring PostgreSQL", "127.0.0.1", 5432, "tcp", "proxmox:lxc:112"),
    ]
    for port in (22, 3000, 3001, 5173, 5181, 8100, 8200):
        protocol: Protocol = "http" if port == 8100 else "tcp"
        targets.append(ProbeTarget(
            f"probe:{protocol}:project-sandbox:{port}",
            f"project-sandbox {protocol} {port}",
            "10.10.10.83",
            port,
            protocol,
            "proxmox:lxc:108",
        ))
    return targets
