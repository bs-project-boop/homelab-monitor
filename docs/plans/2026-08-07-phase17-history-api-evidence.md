# Phase 17 Collector and Status History API Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Read-only history endpoints for dashboard/API consumers  
**Date:** 2026-08-07

## Endpoints

```text
GET /api/v1/collector-runs?limit=50
GET /api/v1/status-events?resource_id=<optional>&limit=100
```

Limits are validated:

```text
collector-runs: 1..100
status-events: 1..200
```

Both endpoints return the existing envelope:

```json
{
  "data": [],
  "source": "...",
  "persistence": "postgresql",
  "freshness": "fresh|empty",
  "partial_errors": []
}
```

## Repository boundary

Added read-only queries:

```text
CollectorRunRepository.list(limit)
StatusEventRepository.list(resource_id, limit)
```

Ordering:

```text
collector runs: started_at DESC
status events: observed_at DESC, id DESC
```

No write or mutation path was added.

## Live API verification

```text
GET /api/v1/collector-runs?limit=2
HTTP 200
rows=2
freshness=fresh

GET /api/v1/status-events?resource_id=docker:110:container:jellyseerr&limit=10
HTTP 200
rows=1
freshness=fresh
```

The filtered event includes the observed `degraded` transition for `jellyseerr`.

## Regression verification

```text
Full pytest: 36 passed
compileall as homelab_monitor: PASS
```

Existing scheduler and collector behavior remains unchanged. The Docker relay timer remains active and continues to produce collector runs independently.
