import os

import pytest

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status
from app.persistence.database import create_session_factory
from app.repositories.sql_resources import ResourceRepository

pytestmark = pytest.mark.asyncio


@pytest.fixture
def session_factory():
    return create_session_factory(os.environ["DATABASE_URL"])


def make_resource() -> Resource:
    return Resource(
        id="test:application:repository",
        kind=ResourceKind.APPLICATION,
        name="repository-test",
        source="test",
        status=Status.UP,
        metadata={"fixture": True},
    )


async def test_upsert_get_list_and_status_event(session_factory) -> None:
    async with session_factory() as session:
        async with session.begin():
            nested = await session.begin_nested()
            repository = ResourceRepository(session)
            resource = make_resource()
            await repository.upsert(resource)
            assert await repository.get(resource.id) == resource
            listed_ids = [item.id for item in await repository.list()]
            assert resource.id in listed_ids
            event_id = await repository.append_status_event(
                resource_id=resource.id,
                previous_status=Status.UNKNOWN,
                status=Status.UP,
                reason="fixture_success",
                metadata={"probe": "test"},
            )
            assert event_id > 0
            await nested.rollback()

    async with session_factory() as session:
        assert await ResourceRepository(session).get("test:application:repository") is None

