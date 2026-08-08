# Phase 6 SQLAlchemy Repository Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Async SQLAlchemy repository against `homelab_monitor`  
**Date:** 2026-08-06

## Implemented

- `backend/app/persistence/database.py`
- `backend/app/persistence/tables.py`
- `backend/app/repositories/sql_resources.py`
- `backend/tests/integration/test_repository_pg.py`

## Repository behavior

- PostgreSQL peer-auth connection through local Unix socket.
- Transactional resource upsert.
- Resource get/list mapping back to the Pydantic domain contract.
- Status event append with generated identity ID.
- Audit timestamps remain persistence-only and are not exposed through `Resource`.

## Verification

Executed as OS user `homelab_monitor` to match PostgreSQL peer authentication:

```text
pytest -p no:cacheprovider -q
16 passed

python -m compileall -q app tests
PASS
```

Integration test uses a savepoint rollback and verifies the fixture row is absent after the transaction boundary. No test data remains in the database.

## Warning

The existing non-blocking Starlette/httpx deprecation warning remains.

## Boundary

`GET /api/v1/resources` still uses the in-memory store in this slice. Switching the API to the SQL repository is intentionally the next end-to-end slice so database configuration, lifecycle, and empty/partial states can be tested together.
