from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.status import Status


class ResourceKind(StrEnum):
    HOST = "host"
    NODE = "node"
    VM = "vm"
    LXC = "lxc"
    DOCKER_HOST = "docker_host"
    CONTAINER = "container"
    APPLICATION = "application"
    SERVICE = "service"
    DEPENDENCY = "dependency"
    CRON_PROFILE = "cron_profile"
    CRON_JOB = "cron_job"
    HERMES_HOST = "hermes_host"
    HERMES_PROFILE = "hermes_profile"
    ARTIFACT = "artifact"


class Resource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: ResourceKind
    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    status: Status = Status.UNKNOWN
    parent_id: str | None = None
    address: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
