# Phase 14 Proxmox API Token Integration Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Dedicated Proxmox API identity, TLS-verified API transport, CLI API mode  
**Date:** 2026-08-06

## Identity and ACL

Created dedicated Proxmox user:

```text
monitor@pve
```

Created API token:

```text
monitor@pve!collector
```

Token privilege separation:

```text
privsep=1
```

ACLs:

```text
path: /
role: PVEAuditor
subject: monitor@pve

path: /
role: PVEAuditor
subject: monitor@pve!collector
```

No lifecycle role was assigned. Existing `root@pam` access was not modified.

## Secret handling

Runtime secret file:

```text
/etc/homelab-monitor/proxmox-api.env
```

Permissions:

```text
600 homelab_monitor:homelab_monitor
```

Parent directory:

```text
750 root:homelab_monitor
```

The token value was piped directly into the runtime file and never printed to chat, evidence, or source code.

CA certificate:

```text
/etc/homelab-monitor/pve-root-ca.pem
```

validates the configured Proxmox API endpoint certificate and IP SAN. The address is deployment configuration and is not committed here.

## Transport

```text
app/services/proxmox_api.py
```

Read-only endpoints:

```text
/api2/json/nodes/pve/status
/api2/json/nodes/pve/lxc
/api2/json/nodes/pve/qemu
```

Authorization header is constructed at runtime and never logged.

## Live verification

Authenticated TLS API smoke:

```text
Proxmox API version: 9.2.3
Resources returned: 14
Errors: []
```

CLI verification:

```bash
python -m app.cli collect --mode api --dry-run
```

Result:

```json
{
  "mode": "api",
  "resource_count": 14,
  "sources": [
    {
      "source": "proxmox",
      "resource_count": 14,
      "errors": []
    }
  ]
}
```

## Test verification

```text
Full pytest suite: 31 passed
compileall as homelab_monitor: PASS
```

## Remaining boundary

Docker collection is not enabled through this API token. Docker data still requires an approved host relay or a separate read-only Docker transport. No Docker socket was exposed to LXC 112.

## Rollback

To roll back this credential change:

```text
revoke monitor@pve!collector
remove token ACL
remove user ACL
remove monitor@pve
remove runtime env file
```

Rollback is intentionally not executed as part of successful verification.
