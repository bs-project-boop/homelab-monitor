#!/usr/bin/env python3
from __future__ import annotations

"""Capture bounded, read-only systemd timer and cron metadata."""
import json
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


def cron_file_metadata(prefix: list[str], *, qga: bool = False) -> tuple[str, str | None]:
    # Return only path + bounded schedule fields; never transport raw cron commands.
    script = r'''for f in $(find /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly -maxdepth 1 -type f -print); do
case "$f" in
  /etc/cron.d/*) schedule=$(awk 'BEGIN{IGNORECASE=1} /^[[:space:]]*#/ || /^[[:space:]]*$/ || /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/ {next} $1 ~ /^@/ {print $1; exit} NF >= 6 {print $1" "$2" "$3" "$4" "$5; exit}' "$f"); printf '%s\t%s\n' "$f" "$schedule" ;;
  *) printf '%s\n' "$f" ;;
esac
done'''
    return run(prefix + ["/bin/sh", "-c", script], qga=qga)


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
