# Phase 13 Live Transport and CLI Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Read-only transport adapters, fixture mode, collector CLI  
**Date:** 2026-08-06

## Transport boundary discovery

From LXC 112:

```text
/usr/bin/ssh exists
SSH to hostname proxmox: unavailable
pvesh: not available in LXC
Docker CLI: not used from LXC host context
```

The LXC cannot directly reach the Proxmox operator hostname. No SSH key, route, DNS entry, or credential was copied or created.

## Implemented

```text
app/services/transport.py
app/cli.py
```

Adapters:

- `SubprocessCommandRunner`
- `ProxmoxPveshSource`
- `DockerPctSource`
- `FixtureSource`

Read-only command contracts:

```text
pvesh get /nodes/<node>/status --output-format json
pvesh get /nodes/<node>/lxc --output-format json
pvesh get /nodes/<node>/qemu --output-format json
pct exec <ct> -- docker version --format '{{json .Server}}'
pct exec <ct> -- docker ps -a --format '{{json .}}'
```

No restart, pull, inspect, environment dump, or lifecycle mutation is performed.

## CLI

Invocation:

```text
python -m app.cli collect --mode fixture --dry-run
```

Result:

```json
{
  "mode": "fixture",
  "resource_count": 29,
  "sources": [
    {"source": "proxmox", "resource_count": 14, "errors": []},
    {"source": "docker", "resource_count": 15, "errors": []}
  ]
}
```

The dry-run performed no database write.

## Verification

```text
Transport tests: PASS
Fixture CLI smoke: PASS
Full pytest suite: 30 passed
compileall as homelab_monitor: PASS
```

## Runtime boundary

`--mode live` is intentionally not registered as a timer yet. It requires the command runner to execute in a Proxmox host context or a separately approved relay transport. The application LXC remains isolated from host SSH credentials and network assumptions.

## Next

- Choose host relay or approved read-only API transport.
- Add live CLI invocation in that execution context.
- Register systemd/Hermes timer only after live CLI smoke passes.
- Add source command stderr redaction and bounded output handling.
