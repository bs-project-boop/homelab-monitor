#!/usr/bin/env python3
from __future__ import annotations

"""Capture bounded, read-only systemd timer and cron metadata."""
import json
import re
import socket
import subprocess
import sys


def run(command: list[str], *, qga: bool = False) -> tuple[str, str | None]:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return "", "command_failed"
    if result.returncode != 0:
        return "", "command_failed"
    if qga:
        try:
            envelope = json.loads(result.stdout)
            if envelope.get("exitcode") != 0 or envelope.get("out-truncated"):
                return "", "guest_command_failed"
            return str(envelope.get("out-data", ""))[:65536], None
        except (TypeError, ValueError):
            return "", "guest_response_invalid"
    return result.stdout[:65536], None


def cron_file_schedule(content: str) -> str:
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\\s*=", line):
            continue
        fields = line.split()
        if fields and fields[0].startswith("@"):
            return fields[0][:40]
        if len(fields) >= 6:
            return " ".join(fields[:5])[:80]
    return "unknown"


def cron_file_metadata(prefix: list[str], *, qga: bool = False) -> tuple[str, str | None]:
    # Return only path + bounded schedule fields; never transport raw cron commands.
    paths, error = run(prefix + ["find", "/etc/cron.d", "/etc/cron.hourly", "/etc/cron.daily", "/etc/cron.weekly", "/etc/cron.monthly", "-maxdepth", "1", "-type", "f", "-print"], qga=qga)
    if error:
        return "", error
    entries: list[str] = []
    for path in paths.splitlines():
        path = path.strip()
        if not path:
            continue
        if path.startswith("/etc/cron.d/"):
            content, content_error = run(prefix + ["head", "-n", "64", path], qga=qga)
            if content_error:
                entries.append(f"{path}\tunknown")
            else:
                entries.append(f"{path}\t{cron_file_schedule(content)}")
        else:
            entries.append(path)
    return "\n".join(entries), None


def target(target_id: str, target_name: str, prefix: list[str], *, qga: bool = False) -> dict[str, object]:
    timers, timer_error = run(prefix + ["systemctl", "list-timers", "--all", "--no-legend", "--plain"], qga=qga)
    crontab, cron_error = run(prefix + ["/bin/sh", "-c", "crontab -l 2>/dev/null || true"], qga=qga)
    cron_files, files_error = cron_file_metadata(prefix, qga=qga)
    errors = [value for value in (timer_error, cron_error, files_error) if value]
    return {"target_id": target_id, "target_name": target_name, "timers": timers, "crontab": crontab, "cron_files": cron_files, "errors": errors}


def lxc_targets() -> list[dict[str, str]]:
    output, error = run(["/usr/bin/ssh", "proxmox", "pct", "list"])
    if error:
        return []
    targets: list[dict[str, str]] = []
    for line in output.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 3 or fields[1] != "running" or not fields[0].isdigit():
            continue
        targets.append({"id": fields[0], "name": " ".join(fields[3:]) if len(fields) > 3 else f"lxc-{fields[0]}"})
    return targets


def main() -> int:
    targets = [
        target("proxmox:node:pve", "pve", ["/usr/bin/ssh", "proxmox"]),
        target("proxmox:vm:111", "omv-8", ["/usr/bin/ssh", "proxmox", "qm", "guest", "exec", "111", "--synchronous", "1", "--timeout", "20", "--"], qga=True),
    ]
    for lxc in lxc_targets():
        targets.append(target(f"proxmox:lxc:{lxc['id']}", lxc["name"], ["/usr/bin/ssh", "proxmox", "pct", "exec", lxc["id"], "--"]))
    encoded = json.dumps({"hostname": socket.gethostname(), "targets": targets}, ensure_ascii=False)
    if len(encoded) > 262144:
        print("scheduler_snapshot_too_large", file=sys.stderr)
        return 2
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
