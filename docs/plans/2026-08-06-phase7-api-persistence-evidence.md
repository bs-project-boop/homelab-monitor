# Phase 7 API Persistence Integration Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** FastAPI resources/readiness backed by PostgreSQL repository  
**Date:** 2026-08-06

## Implemented

- `backend/app/main.py` now uses async SQLAlchemy repository.
- Session dependency creates a scoped session per request.
- `/api/v1/readiness` executes `SELECT 1`.
- `/api/v1/resources` reads PostgreSQL and reports `persistence=postgresql`.
- Missing resources remain `404 resource_not_found`.
- Async engine uses `NullPool` to prevent connection reuse across event loops.

## Verification

Executed as OS user `homelab_monitor`:

```text
Full pytest suite: 18 passed
compileall: PASS
```

Live HTTP smoke:

```json
{"status":"ready","database":"configured"}
```

```json
{"data":[],"source":"inventory","persistence":"postgresql","freshness":"empty","partial_errors":[]}
```

The dev listener was bound to `127.0.0.1:18000` only and was stopped after verification.

## Root cause fixed during verification

The first API integration attempt reused an asyncpg connection across TestClient event loops and failed with `Future attached to a different loop`. The engine now uses `NullPool`, and the full suite passes.

## Warning

The non-blocking Starlette/httpx deprecation warning remains tracked for cleanup.

## Next boundary

- Add collector ingestion service.
- Make collector upserts transactional with status event creation.
- Add Proxmox inventory adapter fixture.
- Add Docker inventory adapter fixture.
