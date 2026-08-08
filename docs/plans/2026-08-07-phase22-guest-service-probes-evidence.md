# Phase 22 Guest and Service Probe Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Read-only TCP/HTTP probes for guest services  
**Date:** 2026-08-07

## Discovery

```text
LXC 108 project-sandbox: 10.10.10.83
LXC 112 monitoring: 10.10.10.55
```

LXC 108 port 25 was excluded because discovery showed it bound only to loopback (`127.0.0.1`/`::1`); probing it remotely would produce a false application failure.

## Probe targets

```text
LXC 112 HTTP 10.10.10.55:18080
LXC 112 TCP 127.0.0.1:5432
LXC 108 TCP 10.10.10.83:22
LXC 108 TCP 10.10.10.83:3000
LXC 108 TCP 10.10.10.83:3001
LXC 108 TCP 10.10.10.83:5173
LXC 108 TCP 10.10.10.83:5181
LXC 108 HTTP 10.10.10.83:8100
LXC 108 TCP 10.10.10.83:8200
```

## Status semantics

```text
TCP success → UP
TCP timeout/connect error → DOWN
HTTP 2xx/3xx → UP
HTTP 4xx/5xx → DEGRADED
```

Probe resources retain parent IDs but do not cascade parent status to children. Error metadata is bounded and does not include credentials or raw payloads.

## CLI

```text
python -m app.probe_cli --dry-run
python -m app.probe_cli
```

`--dry-run` performs no DB write. Commit mode uses the existing transactional collector/orchestrator boundary and creates collector run/status event metadata.

## Dry-run verification

```text
resource_count: 9
statuses: 9 UP
errors: 0
```

## Controlled commit

```text
run_id: b4fb1cdc-7121-4019-8837-cb47dd6a37f3
status: completed
resource_count: 9
error_count: 0
```

Database verification:

```text
probe resources: 9
probe status events: 9
probe collector runs: 1
```

Current total inventory:

```text
resources: 38
status_events: 38
```

## Regression

```text
Full backend pytest: 40 passed
compileall: PASS
```

## Scheduling boundary

No probe timer was enabled. The existing Docker relay timer remains enabled/active on the Proxmox host. Probe cadence requires a separate decision after observing this baseline and selecting timeout/failure policy.
