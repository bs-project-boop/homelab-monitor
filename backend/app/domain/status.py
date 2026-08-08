from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    UNKNOWN = "unknown"
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class StatusPolicy:
    down_failures: int = 3
    recovering_successes: int = 2
    up_successes: int = 5


@dataclass(frozen=True)
class Observation:
    status: Status


def observe(
    current: Status,
    *,
    successes: int,
    failures: int,
    policy: StatusPolicy,
) -> Observation:
    if successes < 0 or failures < 0:
        raise ValueError("successes and failures must not be negative")
    if current is Status.MAINTENANCE:
        return Observation(Status.MAINTENANCE)
    if failures >= policy.down_failures:
        return Observation(Status.DOWN)
    if failures > 0:
        return Observation(Status.DEGRADED)
    if current is Status.DOWN:
        if successes >= policy.recovering_successes:
            return Observation(Status.RECOVERING)
        return Observation(Status.DOWN)
    if current is Status.RECOVERING:
        if successes >= policy.up_successes:
            return Observation(Status.UP)
        return Observation(Status.RECOVERING)
    if current is Status.UNKNOWN and successes >= 1:
        return Observation(Status.UP)
    if current is Status.DEGRADED and successes >= policy.up_successes:
        return Observation(Status.UP)
    return Observation(current)
