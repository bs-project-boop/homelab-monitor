# Phase 4 Inventory Contract Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Resource model, in-memory repository boundary, and read-only API contract  
**Date:** 2026-08-06

## Implemented

- `backend/app/domain/resource.py`
- `backend/app/repositories/resources.py`
- `backend/app/main.py` resource routes
- `backend/tests/unit/test_resource.py`
- `backend/tests/unit/test_repository.py`
- `backend/tests/test_api_resources.py`

## API contract

```text
GET /api/v1/resources
GET /api/v1/resources/{resource_id}
```

Empty inventory response is explicit:

```json
{
  "data": [],
  "source": "inventory",
  "freshness": "empty",
  "partial_errors": []
}
```

Missing resource returns `404` with `resource_not_found`.

## Verification

```text
pytest: 15 passed
compileall: PASS
HTTP /api/v1/resources: 200
HTTP missing resource: 404 resource_not_found
```

## Incident during verification

The first live probe hit a stale development uvicorn process from the previous smoke test, which served the old application and returned generic 404 for `/resources`. The listener was identified by PID, stopped explicitly, the application was restarted from the current source, and the endpoint then returned the expected contract. The dev listener was cleaned up after verification.

## Boundary

Repository is intentionally in-memory for this slice. PostgreSQL persistence and migration are the next boundary; no live collector data is seeded into the API.
