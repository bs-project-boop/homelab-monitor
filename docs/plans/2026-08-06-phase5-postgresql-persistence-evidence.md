# Phase 5 PostgreSQL Persistence Evidence

**Target:** LXC 112 `monitoring`  
**Scope:** Dedicated database and initial Alembic migration  
**Date:** 2026-08-06

## Database

```text
Database: homelab_monitor
Encoding: UTF8
Collation: C
Owner/role: homelab_monitor
PostgreSQL: 17.10
Listen: localhost / Unix socket only
```

The pre-existing default `postgres` database remains untouched.

## Migration

```text
Revision: 0001_initial_inventory
Status: head
```

Tables:

- `resources`
- `status_events`
- `alembic_version`

Indexes include:

- `ix_resources_parent_id`
- `ix_resources_status`
- `ix_resources_source_kind`
- `ix_status_events_resource_time`

## Verification

```text
Alembic upgrade head: PASS
Alembic current: 0001_initial_inventory (head)
Schema query as homelab_monitor: PASS
Alembic upgrade head reapply: PASS / no-op
```

## Safety boundary

`downgrade base` was not executed. It would drop the new tables and is destructive even though this database currently has no application rows. The migration includes a reviewed downgrade implementation for an explicitly approved rollback test.

## Next

- SQLAlchemy persistence repository.
- Mapping Pydantic `Resource` to PostgreSQL rows.
- Transactional upsert and status event append.
- Migration test fixture.
