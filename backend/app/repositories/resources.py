from app.domain.resource import Resource


class ResourceStore:
    def __init__(self) -> None:
        self._resources: dict[str, Resource] = {}

    def upsert(self, resource: Resource) -> Resource:
        self._resources[resource.id] = resource
        return resource

    def get(self, resource_id: str) -> Resource | None:
        return self._resources.get(resource_id)

    def list(self) -> list[Resource]:
        return sorted(self._resources.values(), key=lambda item: (item.name.lower(), item.id))
