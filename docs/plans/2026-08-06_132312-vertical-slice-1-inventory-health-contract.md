# Vertical Slice 1 — Inventory and Health Contract

**Status:** Planning draft for review  
**Target:** LXC 112 `monitoring`  
**Scope:** Proxmox inventory, Docker status, SSH handshake, Hermes cron inventory, overview status.

## Goal

Deliver the smallest complete vertical slice that proves the monitoring architecture against fixtures and selected live LAN sources without collecting raw logs or enabling control actions yet.

## Explicit non-goals

- No interactive SSH terminal yet.
- No arbitrary command execution from the web.
- No automatic restart/remediation.
- No raw log ingestion yet.
- No mutation of Proxmox, Docker, Hermes, or target hosts.
- No public listener.

## Source contracts

### Proxmox

Read-only source for node, VM, LXC, task, storage, and lifecycle metadata. Use a dedicated read-only API credential in the final implementation; development fixtures must not require live credentials.

### Docker

Read-only Docker API/CLI adapter per Docker host. First live fixtures: CT 107 `docker` and CT 110 `servarr`. Preserve container state and healthcheck state separately. `jellyseerr` unhealthy is an expected real-world fixture, not a reason to restart it.

### SSH

First slice performs only TCP connect and SSH handshake. Record target, port, latency, host-key result, authentication result category, and failure category. Do not store private keys or command output.

### Hermes on macOS

macOS is a first-class monitored host, separate from Proxmox and LXC resources. The first live identity is `Bintangs-Mac-mini.local` at `10.10.10.65`.

The status tree is:

```text
macOS host
└── Hermes installation/runtime
    ├── Gateway/scheduler
    └── Profile
        ├── profile gateway
        ├── profile cron scheduler
        └── cron jobs
```

Use a lightweight outbound Mac collector/heartbeat as the preferred design. The collector reports host reachability, Hermes runtime health, profile registry, scheduler heartbeat, and job execution metadata to LXC 112. The dashboard must not infer that Hermes is down merely because the Mac is asleep; it should show `unknown`/`unobserved` with `last_seen` and an explicit reason.

### Hermes cron

Read-only adapter across all configured Hermes profiles. Preserve `profile`, `job_id`, `name`, schedule, state, last run, next run, execution ID, delivery target, workdir/script metadata where safe, and latest result category. Reconcile scheduler heartbeat with job timestamps before classifying stale jobs.

## Domain contract

### Resource

```json
{
  "id": "docker:ct-110:container:jellyseerr",
  "kind": "container",
  "name": "jellyseerr",
  "parent_id": "proxmox:pve:lxc:110",
  "source": "docker",
  "capabilities": ["docker_status", "healthcheck", "ports"],
  "status": "degraded",
  "observed_at": "2026-08-06T...Z"
}
```

IDs are globally namespaced by source and local identity. Parent references must use the same namespace rules.

### Health observation

```json
{
  "resource_id": "docker:ct-110:container:jellyseerr",
  "probe_type": "docker_healthcheck",
  "status": "failed",
  "latency_ms": 12,
  "reason_code": "healthcheck_failed",
  "reason_message": "redacted safe summary",
  "observed_at": "2026-08-06T...Z"
}
```

### Cron resource

```json
{
  "id": "hermes:software-engineering:job:<job_id>",
  "kind": "scheduled_job",
  "name": "job-name",
  "parent_id": "hermes:software-engineering",
  "schedule": "0 8 * * *",
  "state": "active",
  "last_run_at": "2026-08-06T...Z",
  "next_run_at": "2026-08-07T...Z",
  "last_result": "ok",
  "source": "hermes_cron"
}
```

## Status rules

- Direct source status is authoritative for that source only.
- Parent `up` does not imply child `up`.
- Parent collector failure makes children `unknown`/`unobserved`, not automatically `down`.
- Docker `running` and Docker healthcheck `healthy/unhealthy` are separate observations.
- Cron scheduler availability and individual job result are separate observations.
- Status transitions require configurable consecutive observations; initial defaults remain 1 degraded candidate, 3 failures down, 2 successes recovering, 5 successes up.

## Agent access contract

The JSON API/OpenAPI contract is the single client boundary for the web UI, scripts, and Hermes integration. MCP must call the same application service layer or the versioned JSON API; it must not read databases or host files directly.

Initial read-only MCP tools:

- `monitor_overview`
- `monitor_resource_status`
- `monitor_resource_tree`
- `monitor_active_incidents`
- `monitor_recent_events`
- `monitor_search_logs`
- `monitor_cron_status`
- `monitor_collector_health`

Every result includes `observed_at`, `last_seen`, `freshness`, `source`, `scope`, and partial-error information. Log search requires bounded time range, source/resource filters, severity filters, and result limits. Secrets, private keys, tokens, raw credentials, and unsafe command output are never returned.

Hermes can therefore answer questions such as:

- “Apa saja yang down sekarang?”
- “Mengapa aplikasi X down?”
- “Tampilkan log error 30 menit terakhir dari LXC Y.”
- “Cron Hermes profile mana yang gagal?”
- “Apakah Docker container unhealthy?”

No direct Proxmox, Docker, SSH, or Hermes filesystem access is needed for those read-only questions.

## Initial API contract

- `GET /api/v1/health`
- `GET /api/v1/readiness`
- `GET /api/v1/resources`
- `GET /api/v1/resources/{resource_id}`
- `GET /api/v1/resources/{resource_id}/observations`
- `GET /api/v1/cron/jobs`
- `GET /api/v1/collectors`
- `GET /api/v1/incidents?status=active`

All responses include explicit source/capability metadata and scoped errors. A failed source must not suppress healthy results from another source.

## Proposed project paths

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/api/`
- `backend/app/domain/`
- `backend/app/collectors/`
- `backend/app/storage/`
- `backend/tests/unit/`
- `backend/tests/integration/`
- `frontend/src/features/overview/`
- `frontend/src/features/resources/`
- `frontend/src/features/cron/`
- `frontend/src/lib/api/`
- `docs/contracts/`
- `deploy/systemd/`

## Test and verification gate

Before live probes:

- Unit tests for namespaced IDs and status transitions.
- Contract tests for partial source failure.
- Docker fixture tests for running/healthy versus running/unhealthy.
- Cron fixture tests across multiple Hermes profiles with duplicate local job IDs.
- SSH fixture tests for timeout, refused, host-key mismatch, and successful handshake.
- API tests for pagination/filtering and scoped errors.

Live verification after implementation:

- Proxmox source is read-only.
- CT 107 and CT 110 Docker inventories are visible.
- `jellyseerr` remains reported unhealthy without restart.
- SSH handshake reports real status for approved targets.
- All Hermes profiles are represented with profile-scoped jobs.
- Overview shows parent/child status without false cascade.
- `/health` and `/readiness` distinguish process health from collector readiness.

## Approval boundary

No dependency installation, credential configuration, database creation, service unit, or live collector is created until this contract and its open credential/access choices are approved.
