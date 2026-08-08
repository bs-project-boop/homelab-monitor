# Phase 25 Frontend Incident Panel Evidence

**Target:** LXC 112 `monitoring`  
**URL:** `http://10.10.10.55:18080`  
**Date:** 2026-08-07

## Implementation

Added typed incident API contract:

```text
GET /api/v1/incidents?status=open&limit=6
```

Frontend behavior:

- bounded open-incident list;
- warning/critical severity labels and text;
- resource ID and last-seen time;
- accessible `Open incidents` region with `aria-live="polite"`;
- empty state: `No open incidents observed.`;
- partial error state that preserves overview and timeline;
- refresh and 60-second auto-refresh include incident data;
- no credentials or secret values in source or bundle.

## TDD

Initial RED tests failed because `fetchIncidents` was not defined. After implementation:

```text
focused incident client tests: 2 passed
full frontend tests: 5 passed
```

## Build

```text
npm run build: PASS
```

Served bundle:

```text
/assets/index-a8XLAiXc.js
/assets/index-BtwVwK-h.css
```

Bundle marker verification:

```text
incident API route marker: PASS
Open incidents UI marker: PASS
```

Static artifact permissions:

```text
homelab_monitor:homelab_monitor 644
```

## Live browser verification

Desktop LAN URL loaded successfully:

```text
http://10.10.10.55:18080/
title: Homelab Monitor
```

DOM confirmed:

```text
Monitoring overview
38 resources
Open incidents
1
jellyseerr is degraded
docker:110:container:jellyseerr
WARNING
```

Current desktop overflow check:

```text
viewport width: 1280
client width: 1265
scroll width: 1265
horizontal overflow: none
```

## Limitation

Automated mobile resize was not available because the local Playwright MCP browser could not find the Chrome distribution at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. Existing CSS includes the mobile breakpoint at `max-width: 760px` and reduced-motion support, but mobile visual verification remains pending until a Chromium/Chrome browser is installed in the approved execution environment.

No temporary preview server was started; verification used the existing LAN nginx deployment.
