#!/usr/bin/env python3
"""Relay system scheduler metadata to the canonical monitor API."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys

LOCK_PATH = Path("/tmp/com.beem.homelab-monitor-system-scheduler.lock")
SNAPSHOT = Path("/Users/beem/.hermes/profiles/software-engineering/scripts/hermes_monitor_scheduler_snapshot.py")


def main() -> int:
    LOCK_PATH.touch(mode=0o600, exist_ok=True)
    with LOCK_PATH.open("r+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("scheduler_relay_already_running", file=sys.stderr)
            return 75
        try:
            snapshot = subprocess.run([sys.executable, str(SNAPSHOT)], check=False, capture_output=True, text=True, timeout=120)
            if snapshot.returncode != 0:
                sys.stderr.write(snapshot.stderr[-2000:])
                return snapshot.returncode or 2
            payload = json.loads(snapshot.stdout)
            results = []
            for target in payload.get("targets", []):
                relay = subprocess.run(
                    ["/usr/bin/ssh", "proxmox", "pct", "exec", "112", "--", "runuser", "-u", "homelab_monitor", "--", "env", "PYTHONPATH=/opt/homelab-monitor/backend", "DATABASE_URL=postgresql+asyncpg://homelab_monitor@/homelab_monitor?host=/var/run/postgresql", "/opt/homelab-monitor/backend/.venv/bin/python", "-m", "app.cli", "collect", "--mode", "scheduler"],
                    input=json.dumps(target), check=False, capture_output=True, text=True, timeout=180,
                )
                if relay.returncode != 0:
                    sys.stderr.write(relay.stderr[-2000:])
                    return relay.returncode
                results.append(json.loads(relay.stdout))
            print(json.dumps({"targets": results}, sort_keys=True))
            return 0
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            print(f"scheduler_relay_failed:{type(exc).__name__}", file=sys.stderr)
            return 2
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    raise SystemExit(main())
