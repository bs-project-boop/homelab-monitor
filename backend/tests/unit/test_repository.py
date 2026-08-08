from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status
from app.repositories.resources import ResourceStore


def make_resource(name: str, resource_id: str) -> Resource:
    return Resource(
        id=resource_id,
        kind=ResourceKind.APPLICATION,
        name=name,
        source="fixture",
        status=Status.UP,
    )


def test_store_upsert_replaces_by_global_id() -> None:
    store = ResourceStore()
    store.upsert(make_resource("old", "fixture:application:1"))
    store.upsert(make_resource("new", "fixture:application:1"))
    assert len(store.list()) == 1
    assert store.get("fixture:application:1").name == "new"


def test_store_list_is_sorted_by_name() -> None:
    store = ResourceStore()
    store.upsert(make_resource("zulu", "fixture:application:2"))
    store.upsert(make_resource("alpha", "fixture:application:1"))
    assert [item.name for item in store.list()] == ["alpha", "zulu"]
