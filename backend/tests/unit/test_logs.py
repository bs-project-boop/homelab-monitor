from app.services.logs import normalize_log


def test_normalize_log_redacts_secrets_and_preserves_context():
    result = normalize_log(
        resource_id="docker:110:container:demo",
        source="docker",
        level="error",
        message="request failed token=[TEST_TOKEN] password: [TEST_PASSWORD] Authorization: Bearer ***",
        metadata={"attempt": 1},
    )

    assert result.level == "error"
    assert "abc123" not in result.message
    assert "hunter2" not in result.message
    assert "xyz" not in result.message
    assert "[REDACTED]" in result.message
    assert result.metadata == {"attempt": 1}


def test_normalize_log_bounds_message_and_rejects_unknown_level():
    result = normalize_log(
        resource_id=None,
        source="collector",
        level="verbose",
        message="x" * 10000,
        metadata={},
    )

    assert result.level == "info"
    assert len(result.message) == 4000
