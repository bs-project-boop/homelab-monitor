import pytest

from app.domain.identity import namespaced_id


def test_namespaced_id_prevents_cross_source_collision() -> None:
    assert namespaced_id("docker", "container:42") == "docker:container:42"
    assert namespaced_id("hermes:default", "job:42") == "hermes:default:job:42"
    assert namespaced_id("docker", "container:42") != namespaced_id("hermes:default", "job:42")


def test_namespaced_id_rejects_empty_parts() -> None:
    with pytest.raises(ValueError):
        namespaced_id("", "resource")
    with pytest.raises(ValueError):
        namespaced_id("source", "")
