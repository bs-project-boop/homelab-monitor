from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

TOKEN_PATH = Path(os.getenv("OPERATOR_TOKEN_FILE", "/etc/homelab-monitor/operator-token"))
RECOVERY_PATH = Path(os.getenv("OPERATOR_RECOVERY_FILE", "/etc/homelab-monitor/operator-recovery"))
RELAY_SOCKET = os.getenv("ACCESS_RELAY_SOCKET", "/run/homelab-monitor/access-relay.sock")
AUDIT_PATH = Path(os.getenv("ACCESS_AUDIT_FILE", "/var/log/homelab-monitor/access-broker.jsonl"))
SESSION_SECONDS = 7200

TARGETS: dict[str, dict[str, object]] = {
    "pve": {"label": "Proxmox node", "modes": ["shell", "logs"]},
    **{f"lxc-{vmid}": {"label": f"LXC {vmid}", "modes": ["shell", "logs"]} for vmid in (101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 997)},
    "worker-recyclarr": {"label": "Docker worker: recyclarr", "modes": ["logs"]},
    "worker-unpackerr": {"label": "Docker worker: unpackerr", "modes": ["logs"]},
}


@dataclass
class Session:
    session_id: str
    target: str
    mode: str
    expires_at: float


class CreateSessionRequest(BaseModel):
    target: str = Field(min_length=1, max_length=64)
    mode: Literal["shell", "logs"] = "logs"


class BootstrapSecretRequest(BaseModel):
    recovery_secret: str = Field(min_length=32, max_length=256)


class BootstrapResponse(BaseModel):
    operator_token: str
    recovery_secret: str


class SessionResponse(BaseModel):
    session_id: str
    target: str
    mode: str
    expires_at: float


router = APIRouter(prefix="/api/v1/access", tags=["access"])
sessions: dict[str, Session] = {}


def _read_secret(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value if len(value) >= 32 else None


def _write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(mode=0o750, exist_ok=True)
    path.write_text(value + "\n", encoding="utf-8")
    os.chmod(path, 0o640)


def _token() -> str:
    value = _read_secret(TOKEN_PATH)
    if value is None:
        raise HTTPException(status_code=503, detail="operator_auth_not_configured")
    return value


def _recovery_secret() -> str:
    value = _read_secret(RECOVERY_PATH)
    if value is None:
        raise HTTPException(status_code=503, detail="recovery_not_configured")
    return value


def _authorized(authorization: str | None) -> bool:
    expected = _token()
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    return bool(supplied) and secrets.compare_digest(supplied, expected)


def _recovery_authorized(supplied: str) -> bool:
    return bool(supplied) and secrets.compare_digest(supplied.strip(), _recovery_secret())


def _audit(event: dict[str, object]) -> None:
    AUDIT_PATH.parent.mkdir(mode=0o750, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"ts": time.time(), **event}, separators=(",", ":")) + "\n")


@router.get("/bootstrap/status")
def bootstrap_status() -> dict[str, bool]:
    return {"configured": _read_secret(TOKEN_PATH) is not None, "recovery_available": _read_secret(RECOVERY_PATH) is not None}


@router.post("/bootstrap/enroll", response_model=BootstrapResponse, status_code=201)
def bootstrap_enroll() -> BootstrapResponse:
    if _read_secret(TOKEN_PATH) is not None:
        raise HTTPException(status_code=409, detail="operator_auth_already_configured")
    operator_token = secrets.token_urlsafe(48)
    recovery_secret = secrets.token_urlsafe(48)
    _write_secret(TOKEN_PATH, operator_token)
    _write_secret(RECOVERY_PATH, recovery_secret)
    _audit({"event": "operator_bootstrap_enrolled"})
    return BootstrapResponse(operator_token=operator_token, recovery_secret=recovery_secret)


@router.post("/bootstrap/recover", response_model=BootstrapResponse)
def bootstrap_recover(payload: BootstrapSecretRequest) -> BootstrapResponse:
    if not _recovery_authorized(payload.recovery_secret):
        raise HTTPException(status_code=401, detail="invalid_recovery_secret")
    operator_token = secrets.token_urlsafe(48)
    recovery_secret = secrets.token_urlsafe(48)
    _write_secret(TOKEN_PATH, operator_token)
    _write_secret(RECOVERY_PATH, recovery_secret)
    sessions.clear()
    _audit({"event": "operator_bootstrap_recovered"})
    return BootstrapResponse(operator_token=operator_token, recovery_secret=recovery_secret)


@router.get("/targets")
def list_access_targets(authorization: str | None = Header(default=None)) -> dict[str, object]:
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="operator_auth_required")
    return {"data": [{"id": key, **value} for key, value in TARGETS.items()]}


@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_access_session(
    payload: CreateSessionRequest,
    authorization: str | None = Header(default=None),
) -> SessionResponse:
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="operator_auth_required")
    target = TARGETS.get(payload.target)
    if not target or payload.mode not in target["modes"]:
        raise HTTPException(status_code=400, detail="target_mode_not_allowed")
    now = time.time()
    for session_id, existing in list(sessions.items()):
        if existing.expires_at <= now:
            sessions.pop(session_id, None)
    session = Session(uuid.uuid4().hex, payload.target, payload.mode, now + SESSION_SECONDS)
    sessions[session.session_id] = session
    _audit({"event": "session_created", "session": session.session_id, "target": session.target, "mode": session.mode})
    return SessionResponse(session_id=session.session_id, target=session.target, mode=session.mode, expires_at=session.expires_at)


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_access_session(session_id: str, authorization: str | None = Header(default=None)) -> None:
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="operator_auth_required")
    session = sessions.pop(session_id, None)
    if session:
        _audit({"event": "session_revoked", "session": session.session_id, "target": session.target, "mode": session.mode})


async def _relay_request(session: Session) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    reader, writer = await asyncio.open_unix_connection(RELAY_SOCKET)
    writer.write((json.dumps({"session": session.session_id, "target": session.target, "mode": session.mode}) + "\n").encode())
    await writer.drain()
    return reader, writer


def _websocket_token(websocket: WebSocket) -> str:
    protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
    return protocols[1].strip() if len(protocols) > 1 else ""


@router.websocket("/sessions/{session_id}/stream")
async def access_stream(websocket: WebSocket, session_id: str) -> None:
    session = sessions.get(session_id)
    if not session or session.expires_at <= time.time() or not secrets.compare_digest(_websocket_token(websocket), _token()):
        await websocket.close(code=4401)
        return
    await websocket.accept(subprotocol="homelab-operator")
    try:
        reader, writer = await _relay_request(session)
    except OSError:
        await websocket.send_json({"type": "error", "error": "access_relay_unavailable"})
        await websocket.close(code=1011)
        return

    async def relay_to_browser() -> None:
        while True:
            line = await reader.readline()
            if not line:
                return
            await websocket.send_text(line.decode("utf-8", "replace").rstrip("\n"))

    async def browser_to_relay() -> None:
        while True:
            message = await websocket.receive_text()
            if len(message) > 16384:
                continue
            writer.write((message + "\n").encode())
            await writer.drain()

    tasks = [asyncio.create_task(relay_to_browser()), asyncio.create_task(browser_to_relay())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()
        try:
            writer.write(b'{"type":"close"}\n')
            await writer.drain()
        except (ConnectionError, RuntimeError):
            pass
        writer.close()
        await writer.wait_closed()
        sessions.pop(session_id, None)
        _audit({"event": "session_closed", "session": session.session_id, "target": session.target, "mode": session.mode})
