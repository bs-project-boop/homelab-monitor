# Phase 12 Scheduled Collector Execution Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Per-source timeout, source isolation, PostgreSQL advisory lock  
**Date:** 2026-08-06

## Implemented

```text
app/services/scheduler.py
```

Policy:

- One PostgreSQL transaction per scheduled run.
- Transactional advisory lock key: `homelab-monitor:collector`.
- Concurrent run returns `skipped` with `collector_lock_busy`.
- Each source has an independent timeout.
- Source timeout becomes a partial error, not a process-wide failure.
- Source exceptions become typed partial errors using exception type only.
- Successful source resources continue through normal ingestion.

## Verification

```text
Timeout isolation test: PASS
Lock contention test: PASS
Full pytest suite: 28 passed
compileall as homelab_monitor: PASS
```

Lock contention behavior:

```json
{
  "status": "skipped",
  "errors": [
    {
      "source": "scheduler",
      "message": "collector_lock_busy"
    }
  ]
}
```

## Data safety

- Scheduler tests use transaction rollback.
- No duplicate collector run was created by lock contention tests.
- Existing observed inventory remains 29 resources.
- Existing committed collector run remains the single live run.
- No Proxmox/Docker lifecycle operation was executed.

## Boundary

The scheduling policy is implemented but not registered with cron, systemd, or Hermes cron yet. Runtime source transport still needs to be connected to the live SSH/API capture path before enabling periodic execution.

## Next

- Add explicit live source transport adapters.
- Add scheduler CLI entrypoint with structured exit codes.
- Add systemd timer or Hermes cron only after transport verification.
- Add status event history API.
