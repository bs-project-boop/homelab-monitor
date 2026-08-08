import json

from app.services.transport import docker_relay_sources


def test_docker_relay_payload_is_normalized_without_raw_labels() -> None:
    payload = {
        "107": {
            "version": {"Version": "26.1.5"},
            "containers": [
                {
                    "ID": "abc",
                    "Names": "portainer",
                    "Image": "portainer:latest",
                    "State": "running",
                    "Status": "Up",
                    "Labels": "secret=value",
                    "Networks": "bridge",
                }
            ],
        }
    }
    sources = docker_relay_sources(payload)
    assert len(sources) == 1
    assert len(sources[0].source.resources) == 2
    container = sources[0].source.resources[1]
    assert container.metadata.get("labels") is None
    assert container.metadata["docker_state"] == "running"


def test_docker_relay_rejects_malformed_json_shape() -> None:
    try:
        docker_relay_sources({"107": {"containers": "not-a-list"}})
    except ValueError as exc:
        assert str(exc) == "docker_relay_containers_must_be_array"
    else:
        raise AssertionError("expected malformed relay payload rejection")
