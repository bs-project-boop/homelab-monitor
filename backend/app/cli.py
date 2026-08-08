import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict

from app.persistence.database import create_session_factory
from app.services.scheduler import ScheduledCollector, SourceDefinition
from app.services.proxmox_api import ProxmoxApiSource
from app.services.transport import (
    DockerPctSource,
    FixtureSource,
    ProxmoxPveshSource,
    SubprocessCommandRunner,
    docker_relay_sources,
    hermes_relay_sources,
    scheduler_relay_sources,
    fixture_sources,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homelab-monitor-collector")
    parser.add_argument("collect", choices=["collect"])
    parser.add_argument("--mode", choices=["fixture", "api", "relay", "hermes", "scheduler", "live"], default="fixture")
    parser.add_argument("--fixture-root", default="/opt/homelab-monitor/docs/fixtures")
    parser.add_argument("--node", default="pve")
    parser.add_argument("--docker-container", action="append", default=None)
    parser.add_argument("--pve-env", default="/etc/homelab-monitor/proxmox-api.env")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def load_env(path: str) -> None:
    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key] = value


async def execute(args: argparse.Namespace) -> int:
    runner = SubprocessCommandRunner()
    docker_ids = args.docker_container or ["107", "110"]
    if args.mode == "relay":
        source_objects = docker_relay_sources(json.load(sys.stdin))
    elif args.mode == "hermes":
        source_objects = hermes_relay_sources(json.load(sys.stdin))
    elif args.mode == "scheduler":
        source_objects = scheduler_relay_sources(json.load(sys.stdin))
    elif args.mode == "api":
        load_env(args.pve_env)
        source_objects = [
            ProxmoxApiSource(
                base_url=os.environ["PVE_API_URL"],
                token=os.environ["PVE_API_TOKEN"],
                ca_cert=os.environ["PVE_API_CA_CERT"],
                node_name=args.node,
            )
        ]
    elif args.mode == "fixture":
        source_objects = fixture_sources(args.fixture_root)
    else:
        source_objects = [ProxmoxPveshSource(runner, node_name=args.node)] + [
            DockerPctSource(runner, container_id=container_id)
            for container_id in docker_ids
        ]
    if args.mode == "relay":
        definitions = [SourceDefinition(source.source.source, source.fetch) for source in source_objects]
    elif args.mode == "hermes":
        definitions = [SourceDefinition("hermes", source_objects[0].fetch)]
    elif args.mode == "scheduler":
        definitions = [SourceDefinition("system-scheduler", source_objects[0].fetch)]
    elif args.mode == "api":
        definitions = [SourceDefinition("proxmox", source_objects[0].fetch)]
    else:
        definitions = [SourceDefinition(source.source if isinstance(source, FixtureSource) else "proxmox", source.fetch) for source in source_objects]
    if args.mode == "live":
        definitions = [SourceDefinition("proxmox", source_objects[0].fetch)] + [
            SourceDefinition(f"docker:{container_id}", source.fetch)
            for container_id, source in zip(docker_ids, source_objects[1:])
        ]

    if args.dry_run:
        results = [await definition.fetch() for definition in definitions]
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "sources": [
                        {"source": result.source, "resource_count": len(result.resources), "errors": result.errors}
                        for result in results
                    ],
                    "resource_count": sum(len(result.resources) for result in results),
                },
                sort_keys=True,
            )
        )
        return 0

    factory = create_session_factory(os.environ["DATABASE_URL"])
    async with factory() as session:
        result = await ScheduledCollector(session).run(
            definitions, timeout_seconds=args.timeout
        )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.status in {"completed", "partial"} else 2


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(execute(args)))


if __name__ == "__main__":
    main()
