from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


def test_resource_requires_global_id_and_preserves_parent() -> None:
    resource = Resource(
        id="docker:container:42",
        kind=ResourceKind.CONTAINER,
        name="jellyseerr",
        source="docker",
        parent_id="docker:host:ct-110",
        status=Status.DEGRADED,
        metadata={"health": "unhealthy"},
    )
    assert resource.id == "docker:container:42"
    assert resource.parent_id == "docker:host:ct-110"
    assert resource.status is Status.DEGRADED


def test_resource_kind_is_serializable() -> None:
    resource = Resource(
        id="proxmox:lxc:110",
        kind=ResourceKind.LXC,
        name="servarr",
        source="proxmox",
        status=Status.UP,
    )
    assert resource.model_dump(mode="json")["kind"] == "lxc"
