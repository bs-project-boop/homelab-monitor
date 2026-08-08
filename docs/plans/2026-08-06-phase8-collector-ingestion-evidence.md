# Phase 8 Collector Ingestion Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Proxmox fixture normalization and transactional ingestion  
**Date:** 2026-08-06

## Implemented

- `backend/app/collectors/proxmox.py`
- `backend/app/services/ingestion.py`
- `backend/tests/collectors/test_proxmox.py`
- `backend/tests/integration/test_ingestion.py`

## Proxmox normalization

- Node becomes `proxmox:node:<node_name>`.
- LXC becomes `proxmox:lxc:<vmid>`.
- QEMU VM becomes `proxmox:vm:<vmid>`.
- Guest resources point to the Proxmox node parent.
- Lifecycle status maps to domain status without inventing health detail.
- Unknown lifecycle values become `UNKNOWN`.

## Ingestion behavior

- Reads previous resource state.
- Upserts current resource.
- Appends a status event for new resources or status transitions.
- Does not append duplicate events when status is unchanged.
- Caller owns the database transaction boundary.

## Verification

```text
Full pytest suite: 21 passed
compileall: PASS
Fixture rollback: PASS
Residual fixture rows: 0
```

## Safety boundary

No live Proxmox API call was made in this slice. The adapter only consumes an explicit snapshot fixture. Live read-only Proxmox credentials and API wiring remain a separate controlled change.

## Warning

The non-blocking Starlette/httpx deprecation warning remains tracked.

## Next

- Add live Proxmox API client with read-only response fixture capture.
- Add Docker snapshot normalizer and ingestion fixture.
- Expose collector run metadata and partial source errors.
