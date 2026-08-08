from app.collectors.proxmox import ProxmoxGuestSnapshot, ProxmoxSnapshot, snapshot_to_resources
from app.domain.resource import ResourceKind
from app.domain.status import Status


def test_proxmox_snapshot_normalizes_hierarchy() -> None:
    snapshot = ProxmoxSnapshot(
        node_name="pve",
        node_status="online",
        guests=[
            ProxmoxGuestSnapshot(vmid=110, kind="lxc", name="servarr", status="running"),
            ProxmoxGuestSnapshot(vmid=111, kind="qemu", name="omv-8", status="stopped"),
        ],
    )
    resources = snapshot_to_resources(snapshot)

    assert [(item.id, item.kind, item.status) for item in resources] == [
        ("proxmox:node:pve", ResourceKind.NODE, Status.UP),
        ("proxmox:lxc:110", ResourceKind.LXC, Status.UP),
        ("proxmox:vm:111", ResourceKind.VM, Status.DOWN),
    ]
    assert resources[1].parent_id == "proxmox:node:pve"


def test_unknown_guest_status_is_unknown() -> None:
    snapshot = ProxmoxSnapshot(
        node_name="pve",
        node_status="online",
        guests=[ProxmoxGuestSnapshot(vmid=112, kind="lxc", name="monitoring", status="unknown")],
    )
    assert snapshot_to_resources(snapshot)[1].status is Status.UNKNOWN
