# Phase 11 Combined Collector Ingestion Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Proxmox + Docker normalized resources, collector run metadata, PostgreSQL ingestion, API exposure  
**Date:** 2026-08-06

## Schema

Migration applied:

```text
0002_collector_runs (head)
```

New table:

```text
collector_runs
```

Fields include run status, start/completion timestamps, resource count, error count, and JSONB partial errors.

## Collector run

Observed live fixtures were ingested in one transaction:

```text
run_id: 50fc0426-3fd6-4ce1-ba52-27c4268095cf
status: completed
resource_count: 29
error_count: 0
```

Sources:

- Proxmox node + 12 LXC + 1 VM: 14 resources
- Docker CT 107: 2 resources
- Docker CT 110: 13 resources

## Database verification

```text
resources: 29
status_events: 29
collector_runs: 1
latest run: completed / 29 resources / 0 errors
```

Resource kinds:

```text
container: 13
lxc: 12
docker_host: 2
node: 1
vm: 1
```

Status events:

```text
up: 28
degraded: 1
```

The degraded resource is the live `jellyseerr` container with Docker status `unhealthy`.

## API verification

```text
GET /api/v1/readiness: ready / configured
GET /api/v1/resources: 29 resources / fresh
GET /api/v1/collector-runs/latest: completed / 29 / 0 errors
```

Smoke assertions:

```text
API_RESOURCES=29
JELLYSEERR_STATUS=degraded
LATEST_RUN_STATUS=completed
```

## Test verification

```text
Full pytest suite: 26 passed
compileall as homelab_monitor: PASS
```

After live ingestion, tests were corrected to avoid assuming an empty production database. Repository tests now assert fixture membership rather than exact global list equality; API tests assert the observed inventory contract.

## Safety

- Source capture remained read-only.
- No Docker or Proxmox lifecycle operation was performed.
- No credential or token was created.
- Database write was limited to the canonical observed inventory and one collector run.
- No destructive cleanup was run.

## Next

- Add scheduled collector execution with lock/timeout policy.
- Add source-level partial errors from live transports.
- Add status event history endpoint and resource detail timeline.
- Add collector run retention policy after approval.
