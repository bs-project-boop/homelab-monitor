# Phase 15 Docker Host Relay Evidence

**Target:** Proxmox host `pve` → LXC 112 `monitoring`  
**Scope:** Read-only Docker collection from CT 107 and CT 110  
**Date:** 2026-08-06

## Relay

Installed host script:

```text
/usr/local/sbin/homelab-monitor-docker-relay
```

Permissions:

```text
755 root:root
```

SHA-256:

```text
33c14be125f95e8cf7965c429953d9d328b02d33b6f64f3b57b87bd719356c19
```

The relay runs only:

```text
pct exec 107 -- docker version --format '{{json .Server}}'
pct exec 107 -- docker ps -a --format '{{json .}}'
pct exec 110 -- docker version --format '{{json .Server}}'
pct exec 110 -- docker ps -a --format '{{json .}}'
```

No Docker socket is mounted into LXC 112. No `docker inspect`, environment dump, pull, restart, stop, start, or delete operation is used.

## Payload boundary

The host relay allowlists:

```text
ID
Names
Image
State
Status
Ports
Networks
```

Raw labels are not forwarded. Only these Compose label values may cross the relay boundary:

```text
com.docker.compose.project
com.docker.compose.service
com.docker.compose.project.working_dir
```

The LXC receives the payload over stdin and invokes:

```text
python -m app.cli collect --mode relay
```

## Verification

Dry-run:

```json
{
  "mode": "relay",
  "resource_count": 15,
  "sources": [
    {"source": "docker:107", "resource_count": 2, "errors": []},
    {"source": "docker:110", "resource_count": 13, "errors": []}
  ]
}
```

Committed relay run:

```text
run_id: 39840bb0-a962-4b57-a8c0-d9df1f23ed19
status: completed
resource_count: 15
error_count: 0
```

Database after ingestion:

```text
resources: 29
collector_runs: 2
latest run: 15 resources / 0 errors / completed
```

Test verification:

```text
Full pytest: 33 passed
compileall as homelab_monitor: PASS
```

## Boundary

The relay is installed but not registered as a timer yet. It is a one-shot read-only host command. Scheduler registration requires deciding the execution owner and cadence; duplicate protection is already provided by the PostgreSQL advisory lock in LXC 112.
