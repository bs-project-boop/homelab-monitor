# Phase 27 Hermes Host/Profile Collector Evidence

**Target:** LXC 112 `monitoring` / Hermes runtime on Mac host  
**Date:** 2026-08-07  
**Status:** PASS with one observed pre-existing warning

## Scope

Added a read-only Hermes snapshot collector on the Mac and a bounded `--mode hermes` ingestion path into the canonical LXC 112 inventory.

The collector reads only:

- `hermes profile list`
- local hostname from Python stdlib

It does not read `.env`, auth files, sessions, provider credentials, gateway state files, or raw logs. It does not modify Hermes configuration or install a scheduler.

## Artifacts

- `app/collectors/hermes.py`
- `app/domain/resource.py`
  - `hermes_host`
  - `hermes_profile`
- `app/services/transport.py`
  - bounded Hermes relay payload validation
- `app/cli.py`
  - `collect --mode hermes`
- Mac-side snapshot and relay scripts maintained under the Phase 27 working artifact paths.

## Discovery

Live Hermes CLI reported 6 profiles:

- default
- assistant
- platform-reliability
- researcher
- software-engineering
- sysadmin

All reported gateway state `running`. `hermes gateway status` also reported launchd supervision. It reported a stale service definition; this was not modified because it is outside the monitoring collector scope.

## Verification

RED:

- Initial parser tests failed on the active profile row because Hermes uses a different spacing pattern for that row.
- Parser was changed to locate the gateway token as a semantic boundary.

GREEN:

```text
Hermes collector tests: 2 passed
Full backend tests: 48 passed
compileall: PASS
```

Dry-run from live Mac snapshot:

```json
{"mode":"hermes","resource_count":7,"sources":[{"errors":[],"resource_count":7,"source":"hermes"}]}
```

First real relay:

```json
{"error_count":0,"resource_count":7,"status":"completed"}
```

Second real relay:

```text
Hermes resources: 7
Hermes status events: 7
```

The stable resource count and status-event count confirm idempotent ingestion.

API verification after one controlled API restart (required to load the expanded enum into the long-running Uvicorn process):

```text
/api/v1/readiness → ready/configured
/api/v1/overview → resource_count=45, hermes=7, latest collector status=completed
/api/v1/resources → hermes_count=7, secret_markers=false
```

## Security

The live snapshot payload was checked for:

```text
token|password|secret|api_key|Bearer
```

Result: no matches.

Metadata persisted for profiles is limited to model, gateway state, alias, and distribution. Values are length-bounded. Hostname and snapshot output are validated before ingestion.

## Observed risk

- Hermes gateway launchd plist is stale relative to the current Hermes installation. The gateway remains supervised and running. No remediation was applied in this phase.
- The collector is currently manually runnable via the Mac relay script. No Hermes cron or launchd scheduler was installed; scheduling is a separate change requiring its own rollback and timing decision.
