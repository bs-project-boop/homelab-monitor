# Phase 3 Domain Foundation Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** namespaced IDs and status state machine only  
**Date:** 2026-08-06

## Implemented

- `backend/app/domain/identity.py`
- `backend/app/domain/status.py`
- `backend/tests/unit/test_identity.py`
- `backend/tests/unit/test_status.py`

## Verification

```text
.venv/bin/pytest -q
9 passed

.venv/bin/python -m compileall -q app tests
PASS
```

## Behavior covered

- Cross-source IDs do not collide.
- Empty source/local IDs are rejected.
- Unknown → up after first success.
- One failure → degraded.
- Three failures → down.
- Stable recovery uses configured thresholds.
- Maintenance is sticky.

## Warning

The suite still emits a non-blocking Starlette deprecation warning from `fastapi.testclient` about `httpx`; it is tracked for cleanup before release.

## Remaining

- Resource/inventory persistence.
- Proxmox adapter.
- Docker adapter.
- SSH probe adapter.
- Hermes profile/cron adapter.
- API resource endpoints.
- Frontend data integration.
