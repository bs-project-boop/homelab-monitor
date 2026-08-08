import argparse
import asyncio
import json
import os

from app.persistence.database import create_session_factory
from app.services.collector import CollectionSourceResult, CollectorOrchestrator
from app.services.probes import default_probe_targets, probe_target

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://homelab_monitor@/homelab_monitor?host=/var/run/postgresql",
)


async def collect_probe_resources():
    targets = default_probe_targets()
    return await asyncio.gather(*(probe_target(target) for target in targets))


async def run(*, dry_run: bool) -> dict[str, object]:
    resources = await collect_probe_resources()
    if dry_run:
        return {
            "mode": "dry-run",
            "resource_count": len(resources),
            "statuses": {resource.id: resource.status.value for resource in resources},
            "errors": [],
        }
    session_factory = create_session_factory(DATABASE_URL)
    async with session_factory() as session:
        result = await CollectorOrchestrator(session).collect(
            [CollectionSourceResult(source="probe", resources=resources)]
        )
        await session.commit()
        return {
            "mode": "commit",
            "run_id": result.run_id,
            "status": result.status,
            "resource_count": result.resource_count,
            "error_count": result.error_count,
            "errors": result.errors,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only guest/service probes")
    parser.add_argument("--dry-run", action="store_true", help="probe without database writes")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(dry_run=args.dry_run)), sort_keys=True))


if __name__ == "__main__":
    main()
