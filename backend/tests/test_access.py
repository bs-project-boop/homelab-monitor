import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app

client = TestClient(app)


def configure_test_auth(tmp_path, monkeypatch):
    token_path = tmp_path / "operator-token"
    token_path.write_text("a" * 64)
    monkeypatch.setattr("app.access.TOKEN_PATH", token_path)
    monkeypatch.setattr("app.access.AUDIT_PATH", tmp_path / "audit.jsonl")
    return "a" * 64


def test_access_requires_operator_token(tmp_path, monkeypatch) -> None:
    configure_test_auth(tmp_path, monkeypatch)
    response = client.post("/api/v1/access/sessions", json={"target": "pve", "mode": "logs"})
    assert response.status_code == 401


def test_access_creates_allowlisted_session(tmp_path, monkeypatch) -> None:
    token = configure_test_auth(tmp_path, monkeypatch)
    response = client.post(
        "/api/v1/access/sessions",
        headers={"Authorization": "Bearer " + token},
        json={"target": "lxc-112", "mode": "logs"},
    )
    assert response.status_code == 201
    assert response.json()["target"] == "lxc-112"


def test_websocket_rejects_invalid_operator_token(tmp_path, monkeypatch) -> None:
    configure_test_auth(tmp_path, monkeypatch)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/access/sessions/nope/stream", subprotocols=["homelab-operator", "wrong-token"]):
            pass


def test_access_rejects_unallowlisted_target(tmp_path, monkeypatch) -> None:
    token = configure_test_auth(tmp_path, monkeypatch)
    response = client.post(
        "/api/v1/access/sessions",
        headers={"Authorization": "Bearer " + token},
        json={"target": "pve;rm -rf /", "mode": "shell"},
    )
    assert response.status_code == 400
