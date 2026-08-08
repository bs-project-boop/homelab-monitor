# Phase 16 Docker Relay Scheduler Evidence

**Target:** Proxmox host `pve`  
**Scope:** systemd service/timer registration for Docker host relay  
**Date:** 2026-08-07

## Units

```text
/etc/systemd/system/homelab-monitor-docker-relay.service
/etc/systemd/system/homelab-monitor-docker-relay.timer
```

Service checksum:

```text
556355bfae7e45e14cbffe2a8ca747667ba5732fb386a2a905c465f693874a89
```

Timer checksum:

```text
3d2534b56f7e1697a9d18eee39549c094b4d0218c934a9d71635935a123d96c8
```

## Schedule

```text
OnCalendar=*:0/5
RandomizedDelaySec=20s
Persistent=true
TimeoutStartSec=90s
```

Timer state:

```text
enabled
active
```

The service is `Type=oneshot`; inactive/dead between successful runs is expected.

## Hardening

```text
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
UMask=0077
```

## Verification

Manual controlled run:

```text
status: completed
resource_count: 15
error_count: 0
run_id: f9af9b8b-9afb-414b-ace3-46a8d2145e58
```

First scheduled tick:

```text
status: completed
resource_count: 15
error_count: 0
run_id: 3f460637-ecbf-46bb-b26d-b58b96077e53
```

Observed timer progression:

```text
07:10:17 timer activation
07:10:24 service completed successfully
next tick: 07:15:04
```

Post-deployment database state:

```text
collector_runs: 4
latest run: 15 resources / 0 errors / completed
```

Final software verification:

```text
Full pytest: 33 passed
compileall: PASS
```

## Safety

The scheduled relay performs only Docker `version` and `ps -a` through `pct exec`. No Docker lifecycle mutation, Docker socket exposure, or credential change occurs during scheduled execution.

## Rollback

Disable the timer and prevent future runs:

```text
systemctl disable --now homelab-monitor-docker-relay.timer
```

The service unit remains installed for reversible re-enable. Existing observed data and collector-run history are not deleted during rollback.
