# Phase 26 Normalized Logs and Incident Evidence

**Target:** LXC 112 `monitoring`  
**URL:** `http://10.10.10.55:18080`  
**Date:** 2026-08-07

## Boundary

Docker relay allowlist was not expanded. No `docker logs` command, Docker socket, arbitrary host command, credential, environment payload, or raw unbounded exception was added.

Logs are derived from already-observed application boundaries:

- resource status transitions;
- collector/source errors;
- incident open evidence.

Monitored workloads remain read-only.

## Normalization and redaction

Implemented `app.services.logs.normalize_log()` with:

- finite levels: `debug`, `info`, `warning`, `error`, `critical`;
- unknown level fallback to `info`;
- 4,000-character message bound;
- redaction for token, password, secret, API key, bearer authorization, private-key blocks, and sensitive query parameters;
- metadata key filtering for secret-like keys;
- preserved resource/source context.

RED/GREEN test result:

```text
secret redaction and bounds tests: 2 passed
```

The local secret-pattern scan only matched synthetic test values and redaction regex fixtures; no production credential was found.

## Persistence

Migration:

```text
0004_logs (head)
```

Table:

```text
logs
├── id
├── resource_id
├── source
├── level
├── message
├── fingerprint
├── observed_at
└── metadata
```

Indexes:

```text
(resource_id, observed_at)
(source, observed_at)
UNIQUE(fingerprint)
```

Resource foreign key uses `ON DELETE CASCADE`, matching current inventory lifecycle. Current resources are not purged by this phase.

## API

```text
GET /api/v1/logs
GET /api/v1/logs?resource_id=<resource_id>&limit=N
```

Response uses the existing bounded envelope:

```text
data, source, persistence, freshness, partial_errors
```

Verification:

```text
GET /api/v1/logs?limit=201 → HTTP 422
GET /api/v1/readiness → ready/configured
```

## Live evidence

A controlled Docker relay run reconciled the existing degraded incident and created one deterministic evidence row:

```text
resource_id: docker:110:container:jellyseerr
level: warning
message: Incident opened: jellyseerr is degraded
fingerprint: incident:docker:110:container:jellyseerr:availability:opened
```

API result for the resource returned the same normalized row.

Idempotency after a second relay run:

```text
logs total: 1
matching target fingerprint rows: 1
```

## Regression

```text
Full backend pytest: 46 passed
compileall: PASS
Alembic current: 0004_logs (head)
```

Non-blocking existing warning:

```text
Starlette/httpx deprecation warning
```

No temporary preview/API process was left running. API service was restarted once to load the new endpoint and remained ready afterward.
