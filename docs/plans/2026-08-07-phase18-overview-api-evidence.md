# Phase 18 Overview API Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Read-only dashboard overview contract  
**Date:** 2026-08-07

## Endpoint

```text
GET /api/v1/overview
```

The endpoint aggregates existing PostgreSQL-backed repositories into:

```text
resource_count
status_counts
kind_counts
source_counts
latest_collector_run
```

It does not create tables, write rows, or invoke collectors.

## Live response verification

```text
HTTP 200
resource_count: 29
status_counts: up=28, degraded=1
freshness: fresh
partial_errors: []
```

Docker source count:

```text
docker: 15
```

Container kind count:

```text
container: 13
```

Latest collector run:

```text
status: completed
```

## Test verification

```text
Full pytest: 37 passed
compileall as homelab_monitor: PASS
```

Existing history endpoints and Docker timer remain operational. The overview is a read-only aggregation boundary intended for the frontend command center.
