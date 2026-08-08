# Homelab Monitoring Inventory Source Matrix

**Status:** Initial read-only discovery
**Observed:** 2026-08-06 WIB
**Runtime target:** LXC 112 `monitoring`

## Proxmox and infrastructure

- Proxmox node: `pve`
  - Source: Proxmox API + SSH/journald
  - Layers: node health, services, tasks, storage, firewall, cluster state
  - Access required: dedicated read-only API token plus host SSH for deep logs
- VM `111` `omv-8`
  - Source: Proxmox API + guest SSH/agent
  - Layers: VM lifecycle, guest OS, services, storage, applications, logs
- LXC `101` `pihole`
- LXC `102` `searxng`
- LXC `103` `immich`
- LXC `104` `cloudflared`
- LXC `105` `nextcloudpi`
- LXC `106` `onlyoffice`
- LXC `107` `docker`
- LXC `108` `project-sandbox`
- LXC `109` `guacamole`
- LXC `110` `servarr`
- LXC `112` `monitoring`
- LXC `997` `tailscale`

LXC sources: Proxmox API/host task logs plus guest SSH/journald/service/application collectors.

## Docker discovery

Docker is present in:

- CT `107` `docker`
  - `portainer` — running
- CT `110` `servarr`
  - `qbittorrent` — running, healthy
  - `prowlarr` — running, healthy
  - `recyclarr` — running
  - `unpackerr` — running
  - `jellyseerr` — running, unhealthy
  - `bazarr` — running, healthy
  - `readarr` — running, healthy
  - `lidarr` — running, healthy
  - `sonarr` — running, healthy
  - `radarr` — running, healthy
  - `jellyfin` — running, healthy
  - `flaresolverr` — running, healthy

Docker collector requirements:

- Docker daemon/API availability
- Container lifecycle and healthcheck
- Restart/OOM/exit state
- Image digest and deployment drift
- Ports, networks, volumes, stdout/stderr
- Compose project and dependency grouping

## Cron sources

### Proxmox host

- `cron.service`
- systemd timers including apt, logrotate, Proxmox update, cleanup, and filesystem scrub
- `/etc/cron.d/` entries including Proxmox backup-related files and homelab mapper
- root crontab
- Proxmox scheduled backup/replication configuration

### Guest containers

Each LXC requires separate collection of:

- systemd timers
- system cron
- user crontabs where authorized
- job output/error logs
- heartbeat/artifact verification where a schedule does not expose reliable result state

### macOS and Hermes

- macOS host: `Bintangs-Mac-mini.local`
  - LAN IP observed: `10.10.10.65`
  - Source: outbound lightweight collector/heartbeat, with SSH as a diagnostic fallback
  - Layers: host reachability, power/sleep visibility, Hermes runtime, profiles, gateways, schedulers, cron executions
- Hermes runtime on macOS
  - Source: authoritative Hermes CLI/runtime/config adapter
  - Access: read-only, profile-scoped, no cron mutation

Status semantics:

- Mac reachable + collector heartbeat fresh: `up`.
- Mac reachable + Hermes gateway/profile failure: Mac `up`, Hermes subtree `degraded`/`down`.
- Mac asleep/offline or collector heartbeat stale: Mac `unknown`/`unobserved`, not automatically `down`.
- Hermes profile with no jobs: profile can be `up` if its gateway/scheduler is healthy; job count zero is not an error.

### Hermes

Observed profiles:

- `default`
- `assistant`
- `platform-reliability`
- `researcher`
- `software-engineering`
- `sysadmin`

The Hermes collector must preserve profile namespace for every job and collect:

- job ID and name
- enabled/paused/completed state
- schedule and repeat policy
- next run and last run
- execution ID
- duration and completion state
- delivery target
- workdir/script/skills metadata where safe
- latest output/error summary
- scheduler/gateway heartbeat

The collector must use authoritative Hermes runtime/CLI/config discovery and report profile access failures explicitly. It must remain read-only.

## Project LXC 108 workload coverage

LXC `108` (`project-sandbox`) is included as an infrastructure resource and each workload is monitored independently. Live listener discovery observed:

- `3000/tcp` — Node process for `/opt/polisi-maling/server.js`
- `3001/tcp` — Node process for `/opt/arus-finance/server.js`
- `8100/tcp` — Uvicorn for `/opt/sport-prediction/current/backend`
- `5173/tcp` — Next.js server
- `5181/tcp` — Python staging server for `/opt/donventures-rebuild/staging_server.py`
- `8200/tcp` — `spotiflac-web`
- `5432/tcp` — local PostgreSQL dependency
- `22/tcp` — SSH management endpoint
- `25/tcp` — local mail service

The monitor must not equate every open port with a website. Each listener becomes an inventory candidate that is classified as application, dependency, management endpoint, mail service, or unknown, then explicitly mapped to an application and health probe.

For each project website/application, collect:

- Process and service identity.
- Listener and expected port.
- HTTP/HTTPS endpoint and health endpoint where available.
- Response status and latency.
- Application logs and stdout/stderr.
- Dependency status, including PostgreSQL.
- Worker/background process status.
- Deploy/release identity and current version where exposed safely.
- CPU, memory, restart, and error state.

A project application may be `up` while its host is `up` but its dependency or worker is `down`. The UI must preserve this distinction and show the project/application tree.

## Initial collector matrix

- Proxmox API collector: node, VM/LXC lifecycle, tasks, storage, scheduled jobs
- Host SSH collector: deep Proxmox journal/service logs and host cron
- Guest SSH collector: OS, systemd, cron, services, ports, mounts, logs
- Docker API collector: daemon, containers, healthchecks, images, networks, volumes, logs
- HTTP/TCP/DNS/TLS probes: endpoint health and latency
- Hermes collector: all profiles, cron registry, scheduler health, execution metadata
- File/journal log collector: normalized raw logs with explicit source and retention

## Initial findings and verification gates

- `jellyseerr` in CT `110` is currently unhealthy; preserve this as a live integration fixture and do not auto-restart it.
- Hermes profile data must be reconciled against authoritative runtime timestamps before declaring a stale job; the first CLI inventory showed mixed historical timestamps across profile data.
- Child state must become `unknown` when its parent collector is unavailable; do not infer child `down` without direct evidence.
- Every unavailable log source must be represented as `not_collected` or `collection_error`, not as an empty log stream.
