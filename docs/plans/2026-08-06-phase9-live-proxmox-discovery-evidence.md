# Phase 9 Live Proxmox Discovery Evidence

**Target:** LXC 112 `monitoring`  
**Source:** read-only `pvesh` over existing SSH operator path  
**Date:** 2026-08-06

## Capture

Raw fixtures:

```text
/opt/homelab-monitor/docs/fixtures/proxmox/node-status.json
/opt/homelab-monitor/docs/fixtures/proxmox/lxc-list.json
/opt/homelab-monitor/docs/fixtures/proxmox/qemu-list.json
```

Observed source:

- Proxmox node: `pve`
- Proxmox version: `pve-manager/9.2.3`
- LXC rows: 12
- QEMU rows: 1

Fixture checksums:

```text
lxc-list.json   1f73b0f5abe4a204186028fc3c0808369e4d4fe1958ef2f96e239b93a7531974
node-status.json aa545c6865c4204643869106b32e00f60451278cd49614290c81e2e02d6b0c6f
qemu-list.json  6db249edc66bf770dad223dd66776dfb4100fe4430cf56f2400e819eeca77c5e
```

## Parser

`payloads_to_snapshot()` converts the captured pvesh payloads into the existing Proxmox snapshot contract. `snapshot_to_resources()` produces:

```text
1 node
12 LXC
1 VM
14 resources total
```

Required identities observed:

- `proxmox:node:pve`
- `proxmox:lxc:108`
- `proxmox:lxc:110`
- `proxmox:lxc:112`
- `proxmox:vm:111`

## Verification

```text
Proxmox parser tests: PASS
Full pytest suite: 22 passed
compileall as homelab_monitor: PASS
Live fixture parser: 14 resources
Kinds: node=1, lxc=12, vm=1
```

## Boundary

This is a captured live read-only response, not a runtime credentialed collector. No Proxmox API token was created or stored. Runtime wiring remains a separate approved credential/configuration change.

## Next

- Add Docker live snapshot fixture from CT 107 and CT 110.
- Add collector run metadata and partial source errors.
- Decide and approve runtime Proxmox transport: local SSH relay or read-only API token.
