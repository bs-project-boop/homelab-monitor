import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


class ProxmoxGuestSnapshot(BaseModel):
    vmid: int = Field(gt=0)
    kind: Literal["lxc", "qemu"]
    name: str = Field(min_length=1)
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProxmoxSnapshot(BaseModel):
    node_name: str = Field(min_length=1)
    node_status: str
    node_metadata: dict[str, Any] = Field(default_factory=dict)
    guests: list[ProxmoxGuestSnapshot] = Field(default_factory=list)


def _status(value: str) -> Status:
    normalized = value.lower()
    if normalized in {"online", "running", "up"}:
        return Status.UP
    if normalized in {"offline", "stopped", "down"}:
        return Status.DOWN
    if normalized in {"maintenance", "maint"}:
        return Status.MAINTENANCE
    if normalized in {"paused", "degraded"}:
        return Status.DEGRADED
    return Status.UNKNOWN


def snapshot_to_resources(snapshot: ProxmoxSnapshot) -> list[Resource]:
    node_id = f"proxmox:node:{snapshot.node_name}"
    resources = [
        Resource(
            id=node_id,
            kind=ResourceKind.NODE,
            name=snapshot.node_name,
            source="proxmox",
            status=_status(snapshot.node_status),
            metadata={"lifecycle_status": snapshot.node_status, **snapshot.node_metadata},
        )
    ]
    for guest in snapshot.guests:
        kind = ResourceKind.LXC if guest.kind == "lxc" else ResourceKind.VM
        resource_kind = "lxc" if guest.kind == "lxc" else "vm"
        resources.append(
            Resource(
                id=f"proxmox:{resource_kind}:{guest.vmid}",
                kind=kind,
                name=guest.name,
                source="proxmox",
                status=_status(guest.status),
                parent_id=node_id,
                metadata={"vmid": guest.vmid, "lifecycle_status": guest.status, **guest.metadata},
            )
        )
    return resources


def payloads_to_snapshot(
    *, node_name: str, node_payload: dict[str, Any], lxc_payload: list[dict[str, Any]], qemu_payload: list[dict[str, Any]]
) -> ProxmoxSnapshot:
    guests = [
        ProxmoxGuestSnapshot(
            vmid=int(item["vmid"]),
            kind="lxc",
            name=str(item["name"]),
            status=str(item.get("status", "unknown")),
            metadata={key: value for key, value in item.items() if key not in {"vmid", "name", "status", "type"}},
        )
        for item in lxc_payload
    ]
    guests.extend(
        ProxmoxGuestSnapshot(
            vmid=int(item["vmid"]),
            kind="qemu",
            name=str(item["name"]),
            status=str(item.get("status", "unknown")),
            metadata={key: value for key, value in item.items() if key not in {"vmid", "name", "status", "type"}},
        )
        for item in qemu_payload
    )
    node_metadata = {
        key: node_payload[key]
        for key in ("pveversion", "uptime", "loadavg", "memory", "rootfs", "swap")
        if key in node_payload
    }
    return ProxmoxSnapshot(
        node_name=node_name,
        node_status="online",
        node_metadata=node_metadata,
        guests=guests,
    )


def load_json_fixture(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())
