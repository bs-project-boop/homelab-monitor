# Phase 23 Retention and Probe Scheduler Evidence

**Target:** LXC 112 `monitoring`  
**Date:** 2026-08-07

## Retention policy

```text
collector_runs: 30 days
status_events: 90 days
resources: never purged by retention
```

Pre-change PostgreSQL snapshot:

```text
path: /opt/homelab-monitor/artifacts/2026-08-07-pre-retention.dump
mode: 0600
sha256: 48e164c53152ed5cd4d3e8a49ac5a7d8181ac9e87c2af298442bbf0197976521
size: 25263 bytes
```

Retention dry-run and apply both reported:

```text
candidate_collector_runs: 0
candidate_status_events: 0
deleted_collector_runs: 0
deleted_status_events: 0
```

## Probe scheduler

Units:

```text
/etc/systemd/system/homelab-monitor-probes.service
/etc/systemd/system/homelab-monitor-probes.timer
```

Policy:

```text
OnCalendar=*:0/5
RandomizedDelaySec=20s
AccuracySec=1s
Persistent=true
TimeoutStartSec=45s
```

The service is oneshot, runs as `homelab_monitor`, uses the existing probe CLI, and has `NoNewPrivileges`, `PrivateTmp`, `ProtectHome`, `ProtectSystem=full`, address-family restriction, and restrictive umask.

## Manual verification

```text
service exit: 0
status: completed
resource_count: 9
error_count: 0
```

## Real timer tick verification

```text
timestamp: 2026-08-07 07:55:13 UTC
run_id: 2b730d65-6b40-44f1-9d89-f8af6ec73e0d
status: completed
resource_count: 9
error_count: 0
next timer tick: 2026-08-07 08:00:05 UTC
```

Timer state:

```text
enabled
active (waiting)
```

## API and database verification

```text
LAN overview: HTTP 200
resources: 38
source_counts: docker=15, proxmox=14, probe=9
freshness: fresh
```

Resources remain idempotent at 38 despite repeated probe runs. Probe status events remain bounded because events are appended only on status changes.

## Regression

```text
Full backend pytest: 40 passed
compileall: PASS
```

Existing Docker relay timer remains enabled and active on the Proxmox host.
