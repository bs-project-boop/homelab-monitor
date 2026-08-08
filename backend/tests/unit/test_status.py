from app.domain.status import Status, StatusPolicy, observe


def test_initial_success_becomes_up() -> None:
    result = observe(Status.UNKNOWN, successes=1, failures=0, policy=StatusPolicy())
    assert result.status is Status.UP


def test_single_failure_is_degraded() -> None:
    result = observe(Status.UP, successes=0, failures=1, policy=StatusPolicy())
    assert result.status is Status.DEGRADED


def test_repeated_failures_become_down() -> None:
    result = observe(Status.DEGRADED, successes=0, failures=3, policy=StatusPolicy())
    assert result.status is Status.DOWN


def test_recovery_requires_stable_successes() -> None:
    policy = StatusPolicy(recovering_successes=2, up_successes=5)
    recovering = observe(Status.DOWN, successes=2, failures=0, policy=policy)
    healthy = observe(Status.RECOVERING, successes=5, failures=0, policy=policy)
    assert recovering.status is Status.RECOVERING
    assert healthy.status is Status.UP


def test_maintenance_is_sticky_until_explicitly_observed() -> None:
    result = observe(Status.MAINTENANCE, successes=1, failures=0, policy=StatusPolicy())
    assert result.status is Status.MAINTENANCE
