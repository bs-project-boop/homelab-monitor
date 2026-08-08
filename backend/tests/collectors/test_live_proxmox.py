import json
from pathlib import Path

from app.collectors.proxmox import load_json_fixture, payloads_to_snapshot, snapshot_to_resources
from app.domain.resource import ResourceKind
from app.domain.status import Status


FIXTURES = Path("/opt/homelab-monitor/docs/fixtures/proxmox")


def test_captured_live_payload_normalizes_expected_inventory() -> None:
    snapshot = payloads_to_snapshot(
        node_name="pve",
        node_payload=load_json_fixture(FIXTURES / "node-status.json"),
        lxc_payload=load_json_fixture(FIXTURES / "lxc-list.json"),
        qemu_payload=load_json_fixture(FIXTURES / "qemu-list.json"),
    )
    resources = snapshot_to_resources(snapshot)

    assert len(resources) == 14
    assert resources[0].id == "proxmox:node:pve"
    assert resources[0].kind is ResourceKind.NODE
    assert resources[0].status is Status.UP
    assert {resource.id for resource in resources} >= {
        "proxmox:lxc:108",
        "proxmox:lxc:110",
        "proxmox:lxc:112",
        "proxmox:vm:111",
    }
    assert resources[1].metadata["vmid"] > 0
