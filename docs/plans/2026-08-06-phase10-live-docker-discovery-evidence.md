# Phase 10 Live Docker Discovery Evidence

**Target:** LXC 112 `monitoring`  
**Sources:** CT 107 (`docker`) and CT 110 (`servarr`)  
**Date:** 2026-08-06

## Capture

Raw fixtures:

```text
/opt/homelab-monitor/docs/fixtures/docker/ct107-docker-version.json
/opt/homelab-monitor/docs/fixtures/docker/ct107-containers.ndjson
/opt/homelab-monitor/docs/fixtures/docker/ct110-docker-version.json
/opt/homelab-monitor/docs/fixtures/docker/ct110-containers.ndjson
```

Capture used read-only commands:

```text
docker version --format '{{json .Server}}'
docker ps -a --format '{{json .}}'
```

No `docker inspect`, environment dump, restart, pull, or mutation was performed.

## Observed source

- CT 107 Docker Engine: `26.1.5+dfsg1`
- CT 107 containers: 1
- CT 110 Docker Engine: `20.10.24+dfsg1`
- CT 110 containers: 12
- One live unhealthy container: `jellyseerr`

Fixture checksums:

```text
ct107-containers.ndjson      1d7bb2d67eab46d5959f274597e7144c5845f05560a6e17282b95d95a8c07bd6
ct107-docker-version.json    d59d93db6230ff14835a2515b773c4f4bde77beeb8d150b50baa3151888fc520
ct110-containers.ndjson      52a8f1b60ebc2295e2426248bb89afd3c0a473adcb0d4ea72374d65f7baf1e9a
ct110-docker-version.json    efcc9e413874e517002ef1bb3c05ebc8b12757f36d699c8b1ec1138255b51fd2
```

## Normalization

`app/collectors/docker.py` produces:

```text
CT 107: 2 resources
CT 110: 13 resources
Total: 15 resources
```

Each Docker host is attached to its Proxmox LXC parent:

```text
docker:host:107 → proxmox:lxc:107
docker:host:110 → proxmox:lxc:110
```

Each container is attached to its Docker host resource.

Status mapping:

```text
running + healthy → UP
running + unhealthy → DEGRADED
exited/dead → DOWN
paused → DEGRADED
unknown → UNKNOWN
```

Only selected metadata is retained: image, Docker state/status, ports, networks, and compose project/service fields. Raw labels and environment are not stored.

## Verification

```text
Full pytest suite: 24 passed
compileall as homelab_monitor: PASS
Parsed resources: 15
Degraded containers: jellyseerr
```

## Boundary

This slice captures and parses live Docker state only. It does not yet ingest Docker resources into PostgreSQL. That will be combined with Proxmox and ingestion run metadata in the next slice.

## Next

- Add collector run metadata and source partial-error model.
- Ingest Proxmox + Docker resources transactionally.
- Expose current collector state through API.
