from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status
from app.services.incidents import incident_candidate


def resource(status: Status) -> Resource:
    return Resource(
        id="probe:http:project-sandbox:8100",
        kind=ResourceKind.SERVICE,
        name="project-sandbox backend",
        source="probe",
        status=status,
        parent_id="proxmox:lxc:108",
    )


def test_degraded_resource_opens_warning_availability_incident() -> None:
    candidate = incident_candidate(resource(Status.DEGRADED))
    assert candidate is not None
    assert candidate.action == "open"
    assert candidate.severity == "warning"
    assert candidate.fingerprint == "availability"


def test_down_resource_opens_critical_availability_incident() -> None:
    candidate = incident_candidate(resource(Status.DOWN))
    assert candidate is not None
    assert candidate.action == "open"
    assert candidate.severity == "critical"


def test_up_resource_resolves_existing_incident() -> None:
    candidate = incident_candidate(resource(Status.UP))
    assert candidate is not None
    assert candidate.action == "resolve"
    assert candidate.fingerprint == "availability"


def test_unknown_resource_does_not_create_false_incident() -> None:
    assert incident_candidate(resource(Status.UNKNOWN)) is None
