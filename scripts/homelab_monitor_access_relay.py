#!/usr/bin/env python3
"""Privileged, allowlisted access relay for the monitoring LXC."""
from __future__ import annotations

import json
import os
import selectors
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

SOCKET = Path(os.environ.get("ACCESS_RELAY_SOCKET", "/run/homelab-monitor/access-relay.sock"))
MAX_LINE = 16_384
SESSION_SECONDS = 7_200

# Commands are fixed by target and mode. Client input is never used to build a command.
TARGETS: dict[str, tuple[str, ...]] = {
    "pve": ("host",),
    **{f"lxc-{vmid}": ("lxc", str(vmid)) for vmid in (101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 997)},
}


def command_for(target: str, mode: str) -> list[str]:
    spec = TARGETS.get(target)
    if spec is None or mode not in {"logs", "shell"}:
        raise ValueError("target_mode_not_allowed")
    if spec[0] == "host":
        # Host access is deliberately read-only; interactive host shell is not exposed.
        if mode != "logs":
            raise ValueError("target_mode_not_allowed")
        return ["/usr/bin/journalctl", "-n", "100", "--no-pager", "-o", "short-iso"]
    vmid = spec[1]
    if mode == "logs":
        return ["/usr/sbin/pct", "exec", vmid, "--", "/usr/bin/journalctl", "-n", "100", "--no-pager", "-o", "short-iso"]
    return ["/usr/sbin/pct", "exec", vmid, "--", "/bin/sh", "-i"]


def send_line(conn: socket.socket, payload: dict[str, object]) -> None:
    data = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
    conn.sendall(data[:MAX_LINE])


def run_session(conn: socket.socket, request: dict[str, object]) -> None:
    target = request.get("target")
    mode = request.get("mode")
    session_id = request.get("session")
    if not isinstance(target, str) or not isinstance(mode, str) or not isinstance(session_id, str):
        raise ValueError("invalid_session_request")
    command = command_for(target, mode)
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    send_line(conn, {"type": "ready", "session": session_id, "target": target, "mode": mode})
    conn.setblocking(False)
    selector = selectors.DefaultSelector()
    assert proc.stdout is not None and proc.stdin is not None
    selector.register(proc.stdout, selectors.EVENT_READ, "output")
    deadline = time.monotonic() + SESSION_SECONDS
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None and not selector.get_map():
                break
            for key, _ in selector.select(timeout=0.2):
                if key.data == "output":
                    line = proc.stdout.readline()
                    if line:
                        send_line(conn, {"type": "output", "data": line[:MAX_LINE]})
                    else:
                        selector.unregister(proc.stdout)
            try:
                chunk = conn.recv(MAX_LINE)
            except BlockingIOError:
                chunk = b""
            if chunk:
                for line in chunk.splitlines()[:4]:
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if message.get("type") == "close":
                        return
                    if mode == "shell" and message.get("type") == "input":
                        data = message.get("data", "")
                        if isinstance(data, str) and len(data) <= MAX_LINE:
                            proc.stdin.write(data)
                            proc.stdin.flush()
            elif proc.poll() is not None:
                break
        send_line(conn, {"type": "closed", "reason": "expired_or_process_exit"})
    finally:
        selector.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        proc.stdin.close()
        proc.stdout.close()


def main() -> int:
    SOCKET.parent.mkdir(mode=0o755, exist_ok=True)
    try:
        SOCKET.unlink()
    except FileNotFoundError:
        pass
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(SOCKET))
    os.chmod(SOCKET, 0o666)
    listener.listen(8)
    while True:
        conn, _ = listener.accept()
        with conn:
            try:
                conn.settimeout(5)
                raw = conn.recv(MAX_LINE)
                request = json.loads(raw.splitlines()[0])
                run_session(conn, request)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                try:
                    send_line(conn, {"type": "error", "error": str(exc)[:120]})
                except OSError:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
