from pathlib import Path

from app.collectors.docker import load_ndjson, payloads_to_resources
from app.domain.resource import ResourceKind
from app.domain.status import Status

FIXTURES = Path("/opt/homelab-monitor/docs/fixtures/docker")


def test_ct107_snapshot_normalizes_docker_host_and_container() -> None:
    resources = payloads_to_resources(
        container_id="107",
        version={"Version": "26.1.5+dfsg1"},
        containers=load_ndjson(FIXTURES / "ct107-containers.ndjson"),
    )

    assert len(resources) == 2
    assert resources[0].kind is ResourceKind.DOCKER_HOST
    assert resources[1].kind is ResourceKind.CONTAINER
    assert resources[1].parent_id == "docker:host:107"
    assert resources[1].status is Status.UP
    assert resources[1].name == "portainer"


def test_ct110_preserves_unhealthy_container_as_degraded() -> None:
    resources = payloads_to_resources(
        container_id="110",
        version={"Version": "20.10.24+dfsg1"},
        containers=load_ndjson(FIXTURES / "ct110-containers.ndjson"),
    )

    assert len(resources) == 13
    jellyseerr = next(resource for resource in resources if resource.name == "jellyseerr")
    assert jellyseerr.status is Status.DEGRADED
    assert jellyseerr.metadata["compose_service"] == "jellyseerr"
