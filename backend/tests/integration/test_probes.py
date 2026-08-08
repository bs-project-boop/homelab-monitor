from app.domain.resource import ResourceKind
from app.domain.status import Status
from app.services.probes import ProbeObservation, ProbeTarget, observation_to_resource


def test_successful_http_observation_maps_to_up_with_safe_metadata() -> None:
    target = ProbeTarget(
        id="probe:http:monitoring:18080",
        name="monitoring frontend",
        host="10.10.10.55",
        port=18080,
        protocol="http",
        parent_id="proxmox:lxc:112",
    )
    resource = observation_to_resource(
        target,
        ProbeObservation(success=True, latency_ms=3.4, status_code=200),
    )
    assert resource.kind is ResourceKind.SERVICE
    assert resource.status is Status.UP
    assert resource.metadata == {"protocol": "http", "port": 18080, "latency_ms": 3.4, "status_code": 200}


def test_failed_tcp_observation_maps_to_down_without_parent_cascade() -> None:
    target = ProbeTarget(
        id="probe:tcp:project-sandbox:3000",
        name="project-sandbox port 3000",
        host="10.10.10.83",
        port=3000,
        protocol="tcp",
        parent_id="proxmox:lxc:108",
    )
    resource = observation_to_resource(
        target,
        ProbeObservation(success=False, latency_ms=None, error="connect_timeout"),
    )
    assert resource.status is Status.DOWN
    assert resource.parent_id == "proxmox:lxc:108"
    assert resource.metadata["error"] == "connect_timeout"


def test_http_server_error_is_degraded_and_error_is_redacted() -> None:
    target = ProbeTarget(
        id="probe:http:project-sandbox:8100",
        name="project-sandbox backend",
        host="10.10.10.83",
        port=8100,
        protocol="http",
        parent_id="proxmox:lxc:108",
    )
    resource = observation_to_resource(
        target,
        ProbeObservation(success=False, latency_ms=12.0, status_code=503, error="HTTP 503"),
    )
    assert resource.status is Status.DEGRADED
    assert resource.metadata["status_code"] == 503
    assert "10.10.10.83" not in resource.metadata["error"]
