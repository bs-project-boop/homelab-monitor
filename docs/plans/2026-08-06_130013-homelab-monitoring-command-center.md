# Homelab Monitoring Command Center — Planning Plan

**Status:** Draft for review  
**Target:** LXC 112 `monitoring` (`10.10.10.55`)  
**Development boundary:** all source, build, test, and runtime preparation occur inside LXC 112 through `ssh proxmox` + `pct exec`/`pct enter`.

## Goal

Build a local-only, single-operator homelab command center that monitors Proxmox nodes, VMs, LXCs, hosts, ports, applications, dependencies, storage, backups, certificates, and logs, with an audited interactive SSH terminal for explicitly selected targets.

## Product boundary

- LAN/local only; no public Internet exposure.
- Read-only monitoring is the default.
- Interactive SSH is an explicit operator capability.
- No automatic remediation or unattended destructive command in the first release.
- Logs are a separate data plane from current status and incidents.

## Proposed architecture

- Frontend: React + TypeScript + Vite.
- API: FastAPI + Pydantic.
- Database: PostgreSQL for inventory, checks, events, incidents, SSH audit, and indexed logs.
- Background scheduler/worker for probes and collectors.
- SSH: AsyncSSH for interactive sessions and read-only collection.
- Realtime: SSE for status/incidents; WebSocket only for terminal I/O.
- Migrations: Alembic.
- Runtime supervision: systemd in LXC 112.

## Source of truth and agent access

The monitoring application is the canonical source of truth for observed health, status transitions, incidents, inventory, and normalized log metadata. It is not the original source of raw logs or host configuration; every record retains its source, observation time, freshness, and collection status.

The contract boundary is:

```text
Collectors → monitoring database → JSON API/OpenAPI → web UI
                                      └──────────────→ MCP adapter → Hermes agent
```

The JSON API is authoritative and usable by browsers, scripts, and future clients. MCP is an adapter over the same service layer, not a second data implementation. Hermes agents can query overview, resource status, incidents, cron status, logs, and collector freshness through the monitoring endpoint without direct access to Proxmox, Docker, VM/LXC, or Hermes filesystem state.

Agent access is read-only by default and must be scoped, authenticated, rate-limited, paginated, redacted, and freshness-aware. Any future control action requires a separate mutation API and explicit audit boundary; it must not be exposed through read-only monitoring tools.

## Hierarchical observability model

The dashboard must represent health and logs as a parent-child tree, without claiming a child is healthy merely because its parent is reachable:

```text
Proxmox cluster
└── Proxmox node
    └── VM or LXC
        └── Guest OS
            ├── systemd/service
            ├── process/container
            ├── application
            ├── port/endpoint
            ├── database/cache
            └── disk/mount/storage
```

Every level has its own:

- Current indicator: `up`, `degraded`, `down`, `unknown`, or `maintenance`.
- Last successful observation.
- Last failure reason and latency.
- Related logs and status events.
- Parent/child relationship.
- Capability/source indicator showing whether the level is observed through Proxmox API, SSH, guest agent, application probe, syslog/journald, file collector, or another source.

The UI must show both the local state and the derived impact state. For example, a Proxmox node can be `up` while one VM is `down`; a VM can be `up` while its application is `down`; an application can be `up` while its storage is `degraded`.

## Log coverage contract

Log collection is layered and source-specific:

- **Proxmox layer:** task history, node/service logs, cluster state, storage status, VM/LXC lifecycle events, backup jobs, replication, firewall, and API/task failures where available from the Proxmox API and host journal.
- **VM layer:** VM lifecycle and guest integration status from Proxmox, plus guest OS logs via SSH/agent. Hypervisor visibility cannot replace guest-level visibility.
- **LXC layer:** container lifecycle/configuration and host-side task logs from Proxmox, plus guest journald, syslog, service logs, process failures, network errors, and storage/mount errors via SSH/agent.
- **Guest OS layer:** kernel, boot, authentication, systemd, package, disk, filesystem, network, OOM, and security-relevant events.
- **Application layer:** application log files, stdout/stderr, structured JSON logs, HTTP errors, background worker failures, database/cache errors, and application health transitions.
- **Dependency layer:** PostgreSQL, Redis, reverse proxy, DNS, NFS/SMB, backup, TLS, and other configured dependencies.

Each log entry must retain source level, source identity, original timestamp, received timestamp, severity, service/application, message, structured fields, correlation identifiers where available, and redaction status. Missing access must be reported as `not_collected` or `collection_error`, never silently presented as no logs.

Raw logs, normalized searchable events, status history, and incidents remain separate stores with explicit retention policies.

## Docker application coverage

Docker workloads are first-class monitored resources, not merely port entries:

- Docker host and daemon availability.
- Container running/stopped/restarting/paused/created state.
- Healthcheck status and failing health output.
- Exit code, restart count, OOM kill, and start time.
- Image name, image digest, tag, and drift from the declared deployment.
- Published ports and container-network membership.
- CPU, memory, network, and filesystem usage where available.
- Container stdout/stderr logs and application log files.
- Compose/project grouping and service dependencies.
- Volume and bind-mount visibility.

The UI must distinguish container state from application state. A container can be running while the application healthcheck is failing; a published port can be open while the application is returning errors.

## Cron and scheduled-job coverage

All scheduled jobs are monitored as resources with schedule, owner, source, last run, next run, duration, exit state, and output/error metadata.

Coverage includes:

- Host cron and `/etc/cron.*` entries.
- User crontabs for configured homelab hosts.
- systemd timers and their journal output.
- Docker Compose scheduled workers where identifiable.
- Proxmox scheduled backup/replication tasks.
- Hermes cron jobs across all configured Hermes profiles.
- Hermes job enabled/paused state, schedule, delivery target, last run, next run, runtime, completion state, and latest output/error summary.

Cron health must detect:

- Job missed its expected window.
- Job has not run recently.
- Job ran but exited with failure.
- Job ran successfully but produced an error signal.
- Job duration exceeded its baseline.
- Job is disabled or paused unexpectedly.
- Duplicate or overlapping runs.
- Scheduler/worker itself is unavailable.

Cron monitoring is read-only. The dashboard must not create, edit, pause, resume, run, or remove jobs automatically. Any future control action is a separate audited mutation plane.

For Hermes, the collector must discover profiles from the authoritative Hermes configuration/runtime, preserve profile identity in every record, and report inaccessible profiles explicitly. It must not modify Hermes cron state while observing it.

## Core domain model

`nodes`, `resources`, `applications`, `endpoints`, `probes`, `probe_results`, `status_events`, `dependencies`, `log_sources`, `log_entries`, `incidents`, `ssh_profiles`, `ssh_sessions`, and `maintenance_windows`.

## Status contract

States: `unknown`, `up`, `degraded`, `down`, `recovering`, `maintenance`.

Default transitions:

- 1 failed result: degraded candidate.
- 3 consecutive failures: down.
- 2 consecutive successes: recovering.
- 5 consecutive successes: up.

The state machine is centralized; thresholds may be configured per probe.

## UI contract

Primary navigation:

- Overview
- Infrastructure
- Applications
- Logs
- Incidents
- SSH Sessions
- Settings

Overview stays simple. Detail pages provide progressive disclosure:

- Resource: Overview, SSH, Services, Ports, Metrics, Logs, Events.
- Application: Overview, Health, Dependencies, Logs, Incidents.
- SSH: target confirmation, terminal, session status, close/kill, audit reference.

Visual direction: modern, simple, responsive, dark/light theme, limited status colors, no overloaded overview.

## SSH contract

Phase 1 supports explicit target selection, interactive shell over WebSocket-to-AsyncSSH, idle/max duration, kill action, host-key verification, credential profiles without plaintext private keys in the database/browser, and session audit metadata.

Phase 1 excludes unattended arbitrary commands, automatic remediation, browser file transfer, credential export, and public exposure.

## Implementation phases

1. **Discovery/contracts:** project brief, architecture, security boundary, monitoring/SSH/log contracts, ADRs, acceptance criteria.
2. **Runtime foundation:** repository, isolated environments, PostgreSQL schema, migrations, health/readiness, structured logging, config validation.
3. **Inventory/probes:** inventory, ICMP/TCP/HTTP/DNS/TLS/SSH handshake probes, scheduler, immutable results, state transitions, API contracts.
4. **Proxmox/SSH:** read-only Proxmox integration, VM/LXC discovery, SSH inventory, service/port collectors, interactive SSH protocol.
5. **Dashboard:** overview, detail pages, filters/search, incidents, dependencies, responsive/accessibility, realtime updates.
6. **Log plane:** sources, ingestion, normalization, redaction, retention, search, live tail, source health, log-to-incident correlation.
7. **Operations:** Discord alerts, deduplication, recovery notices, maintenance, backup/restore verification, systemd, resource limits, runbooks.
8. **Release verification:** static, unit, contract, integration, terminal, retention, accessibility, performance, security, LAN browser, rollback, post-deployment health.

## Initial acceptance criteria

- Configured host/resource/application status is accurate and source-labelled.
- Failed probes transition and recover according to the state machine.
- TCP, HTTP, TLS, and SSH checks report latency and useful failure reasons.
- Proxmox inventory is read-only.
- Explicitly selected targets support audited interactive SSH.
- Secrets/private keys never appear in API responses, browser storage, or logs.
- Logs are searchable, redacted, retention-bounded, and separate from current status.
- One failed collector does not hide healthy resources from other collectors.
- Dashboard works on desktop, tablet, and mobile.
- Runtime has health/readiness, backup, rollback documentation, and no public listener.

## Open decisions for review

1. PostgreSQL inside LXC 112 versus an existing external PostgreSQL service.
2. Vite React versus Next.js.
3. SSH credentials via SSH agent, root-owned mounted key directory, or dedicated operator key store.
4. Access bind: localhost only versus LAN IP `10.10.10.55`.
5. Proxmox access: read-only API token versus SSH-based `pct` discovery.
6. Initial log sources: journald/SSH polling, file tail, syslog receiver, or agent push.
7. Alert destination: Discord only initially versus Discord plus email/Telegram.
8. Retention targets for raw logs, status history, and incidents.

## Planning gate

Do not install application dependencies or create production service units until the open decisions and contracts are reviewed. The first implementation slice should be inventory + TCP/HTTP/SSH handshake + overview status, with tests and live LAN verification.
