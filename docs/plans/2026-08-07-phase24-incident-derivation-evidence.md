# Phase 24 Incident Derivation Evidence

**Target:** LXC 112 `monitoring`  
**Date:** 2026-08-07

## Contract

Incident derivation is read-only with respect to monitored workloads. It persists the observed incident lifecycle only:

```text
DEGRADED → open / warning
DOWN     → open / critical
UP       → resolved
UNKNOWN  → no incident inference
```

One availability incident is maintained per resource using the unique key:

```text
(resource_id, fingerprint=availability)
```

Parent status is never cascaded into child incidents.

## Persistence

Migration:

```text
0003_incidents (head)
```

Table `incidents` includes:

```text
id, resource_id, fingerprint, status, severity, title,
opened_at, resolved_at, last_seen_at, metadata
```

Foreign key:

```text
incidents.resource_id → resources.id ON DELETE CASCADE
```

Unique constraint:

```text
uq_incidents_resource_fingerprint
```

Rollback is available through the migration downgrade in a controlled non-production environment. No downgrade was executed.

## RED/GREEN

Initial RED test failed because `app.services.incidents` did not exist. After implementation:

```text
Incident semantic tests: 4 passed
Full backend pytest: 44 passed
compileall: PASS
```

## Live derivation

A controlled Docker relay run processed the existing Docker snapshot and derived the real degraded container incident:

```text
resource_id: docker:110:container:jellyseerr
status: open
severity: warning
title: jellyseerr is degraded
```

Database contained exactly:

```text
incidents: 1
open incidents: 1
```

A second relay run preserved idempotency:

```text
incidents after second run: 1
open incidents after second run: 1
```

No duplicate incident row was created.

## API

```text
GET /api/v1/incidents?status=open&limit=10 → HTTP 200
GET /api/v1/incidents?limit=201 → HTTP 422
```

Response uses the existing bounded read-only envelope:

```text
data, source, persistence, freshness, partial_errors
```

LAN readiness after API reload:

```text
GET http://10.10.10.55:18080/api/v1/readiness → ready/configured
```

## Scope and safety

- No workload lifecycle command was executed.
- No Docker socket or raw environment/label payload was exposed.
- No credential was stored or emitted.
- No auto-remediation or external alert was enabled.
- Incident state is derived from observed resource status only.
