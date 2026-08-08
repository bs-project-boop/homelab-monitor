# Phase 20 Frontend Status Timeline Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Read-only recent status-transition timeline in the command center  
**Date:** 2026-08-07

## Implementation

Added typed frontend support for:

```text
GET /api/v1/status-events?limit=8
```

The dashboard now renders:

- recent resource transition rows;
- resource ID;
- transition reason;
- categorical status text and indicator;
- observed local time;
- empty-history state;
- bounded request size.

Overview loading remains independent: a history failure does not hide the main inventory overview.

## Verification

Frontend tests:

```text
3 passed
```

Production build:

```text
npm run build: PASS
```

Live history API:

```text
HTTP 200
rows: 8
freshness: fresh
```

The temporary API process used for the probe was stopped. Port `127.0.0.1:18000` was verified empty afterward.

No production frontend service or LAN preview was enabled.
