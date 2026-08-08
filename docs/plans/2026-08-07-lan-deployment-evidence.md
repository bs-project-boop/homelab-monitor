# LAN Deployment Evidence

**Target:** LXC 112 `monitoring` (`10.10.10.55`)  
**URL:** `http://10.10.10.55:18080`  
**Date:** 2026-08-07

## Deployment boundary

```text
10.10.10.55:18080 nginx
  /       -> /opt/homelab-monitor/frontend/dist
  /api/   -> 127.0.0.1:18000

127.0.0.1:18000 uvicorn monitor API
  -> PostgreSQL via local Unix socket
```

The API port is not exposed on the LAN. The only LAN application listener is nginx on `10.10.10.55:18080`.

## Services

```text
homelab-monitor-api.service: enabled, active
nginx.service: enabled, active
```

API unit:

```text
/etc/systemd/system/homelab-monitor-api.service
sha256: 47b4596f2f116b9465bb35bb79931c38759040901a4972952ab545d27acab46a
```

nginx site:

```text
/etc/nginx/sites-available/homelab-monitor
sha256: 4ee9e58c7c1a2a3a562a62cae96664c1aa4f477831daa5929d2134800b7578ae
```

nginx configuration test:

```text
nginx -t: successful
```

## End-to-end verification

From LXC 112:

```text
GET http://10.10.10.55:18080/ -> HTTP 200
GET /api/v1/readiness -> {"status":"ready","database":"configured"}
GET /api/v1/overview -> 29 resources, up=28, degraded=1, fresh
```

From Proxmox host:

```text
GET http://10.10.10.55:18080/ -> HTTP 200
GET /api/v1/overview -> 29 resources, fresh
```

LAN boundary check:

```text
10.10.10.55:18000 direct access -> blocked
10.10.10.55:18080 nginx access -> allowed
```

## Rollback

- Stop/disable `homelab-monitor-api.service` and `nginx.service`.
- Restore the nginx fallback from `/etc/nginx/sites-available/default.disabled` if needed.
- The previous frontend build remains recoverable from the existing dist artifact/history.

The dashboard is LAN-only HTTP. No DNS, public tunnel, TLS, or internet exposure was configured.
