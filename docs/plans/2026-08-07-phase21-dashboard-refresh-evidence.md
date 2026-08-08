# Phase 21 Dashboard Refresh Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Dashboard refresh behavior for overview and status history  
**Date:** 2026-08-07

## Behavior

The dashboard now:

- loads overview and status history together;
- refreshes automatically every 60 seconds;
- provides an accessible manual `Refresh` button;
- disables the button during an active refresh;
- displays the last successful update time;
- preserves the main overview when the status-history request fails;
- clears the main error after a later successful refresh.

The refresh remains read-only and only calls existing GET endpoints.

## Verification

```text
npm test: 3 passed
npm run build: PASS
```

Bundle checks:

```text
refresh control present: PASS
/api/v1/status-events present: PASS
```

Artifact permissions:

```text
homelab_monitor:homelab_monitor 644
```

Process hygiene:

```text
ports 18000, 4173, 5173: unused
no vite/uvicorn dev process: PASS
```
