from app.collectors.docker_workers import worker_resources


def test_worker_resources_classifies_known_compose_workers_without_commands():
    resources = worker_resources(
        container_id="110",
        containers=[
            {"ID": "abc", "Names": "recyclarr", "Image": "recyclarr/recyclarr:8", "State": "running", "Status": "Up", "Labels": "com.docker.compose.service=recyclarr,com.docker.compose.project=compose"},
            {"ID": "def", "Names": "sonarr", "Image": "linuxserver/sonarr:latest", "State": "running", "Status": "Up", "Labels": "com.docker.compose.service=sonarr"},
        ],
    )
    assert len(resources) == 1
    assert resources[0].name == "recyclarr worker"
    assert resources[0].parent_id == "docker:110:container:recyclarr"
    assert "command" not in resources[0].metadata
    assert "recyclarr" == resources[0].metadata["compose_service"]
