import argparse
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://homelab_monitor@/homelab_monitor?host=/var/run/postgresql",
)
COLLECTOR_RUNS_DAYS = 30
STATUS_EVENTS_DAYS = 90
LOGS_DAYS = 30


async def retention(*, apply: bool) -> dict[str, object]:
    now = datetime.now(UTC)
    run_cutoff = now - timedelta(days=COLLECTOR_RUNS_DAYS)
    event_cutoff = now - timedelta(days=STATUS_EVENTS_DAYS)
    log_cutoff = now - timedelta(days=LOGS_DAYS)
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        run_count = int((await connection.execute(text("select count(*) from collector_runs where started_at < :cutoff"), {"cutoff": run_cutoff})).scalar_one())
        event_count = int((await connection.execute(text("select count(*) from status_events where observed_at < :cutoff"), {"cutoff": event_cutoff})).scalar_one())
        log_count = int((await connection.execute(text("select count(*) from logs where observed_at < :cutoff"), {"cutoff": log_cutoff})).scalar_one())
        deleted_runs = 0
        deleted_events = 0
        deleted_logs = 0
        if apply:
            deleted_runs = int((await connection.execute(text("delete from collector_runs where started_at < :cutoff"), {"cutoff": run_cutoff})).rowcount or 0)
            deleted_events = int((await connection.execute(text("delete from status_events where observed_at < :cutoff"), {"cutoff": event_cutoff})).rowcount or 0)
            deleted_logs = int((await connection.execute(text("delete from logs where observed_at < :cutoff"), {"cutoff": log_cutoff})).rowcount or 0)
    await engine.dispose()
    return {
        "mode": "apply" if apply else "dry-run",
        "generated_at": now.isoformat(),
        "collector_runs_days": COLLECTOR_RUNS_DAYS,
        "status_events_days": STATUS_EVENTS_DAYS,
        "logs_days": LOGS_DAYS,
        "collector_runs_cutoff": run_cutoff.isoformat(),
        "status_events_cutoff": event_cutoff.isoformat(),
        "candidate_collector_runs": run_count,
        "candidate_status_events": event_count,
        "candidate_logs": log_count,
        "deleted_collector_runs": deleted_runs,
        "deleted_status_events": deleted_events,
        "deleted_logs": deleted_logs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply bounded monitoring history retention")
    parser.add_argument("--apply", action="store_true", help="delete rows older than the retention windows")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(retention(apply=args.apply)), sort_keys=True))


if __name__ == "__main__":
    main()
