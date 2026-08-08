from app.collectors.artifacts import artifact_status
from app.domain.status import Status


def test_not_observed_artifact_is_unknown_not_healthy() -> None:
    assert artifact_status({"artifact_status": "not_observed"}) is Status.UNKNOWN


def test_generated_artifact_with_failed_delivery_is_degraded() -> None:
    assert artifact_status({"artifact_status": "generated", "github": {"status": "failed"}}) is Status.DEGRADED
