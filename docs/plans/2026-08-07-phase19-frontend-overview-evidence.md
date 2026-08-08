# Phase 19 Frontend Overview Integration Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** React/Vite command-center overview consuming the typed overview API  
**Date:** 2026-08-07

## Frontend boundary

Added:

```text
frontend/src/api.ts
frontend/src/api.test.ts
```

The API client:

- uses `/api/v1/overview` by default;
- supports `VITE_API_BASE_URL` for an explicit API origin;
- sends `Accept: application/json`;
- exposes typed `OverviewResponse`, `OverviewData`, `CollectorRun`, and status unions;
- converts non-2xx responses into a user-safe error.

## UI

The command center now renders:

- observed inventory count;
- healthy/degraded summary;
- latest collector status and error count;
- source count;
- status distribution with text and color indicators;
- source distribution;
- loading and error states;
- read-only/local scope indicator;
- reduced-motion CSS behavior.

No credentials or environment-specific secrets are embedded.

## Verification

Frontend unit tests:

```text
2 passed
```

Production build:

```text
npm run build: PASS
```

Bundle contract check:

```text
/api/v1/overview present in dist assets: PASS
```

Artifact permissions:

```text
homelab_monitor:homelab_monitor 644
```

Live backend integration:

```text
GET /api/v1/overview → HTTP 200
resource_count: 29
status_counts: up=28, degraded=1
freshness: fresh
```

The temporary API process was stopped after the smoke test. No preview server or production frontend service was enabled.
