from app.collectors.hermes import profile_list_to_resources, parse_profile_list

PROFILE_OUTPUT = """Profile          Model                        Gateway      Alias        Distribution
 ───────────────    ───────────────────────────    ───────────    ───────────    ────────────────────
  default         MiniMax-M2.7                 running      —            —
 ◆software-engineering gpt-5.6-luna                 running      —            —
  researcher      minimax-m2.7                 running      researcher   —
"""


def test_parse_profile_list_preserves_safe_fields_only():
    profiles = parse_profile_list(PROFILE_OUTPUT)
    assert [profile.name for profile in profiles] == ["default", "software-engineering", "researcher"]
    assert profiles[1].active is True
    assert profiles[2].alias == "researcher"


def test_profile_list_to_resources_builds_stable_host_hierarchy():
    resources = profile_list_to_resources(PROFILE_OUTPUT, hostname="Bintangs-Mac-mini.local")
    assert len(resources) == 4
    assert resources[0].id == "hermes:host:Bintangs-Mac-mini.local"
    assert resources[1].id == "hermes:Bintangs-Mac-mini.local:profile:default"
    assert resources[1].parent_id == resources[0].id
    assert resources[1].metadata == {"model": "MiniMax-M2.7", "gateway": "running", "alias": "—", "distribution": "—"}
    assert all("token" not in str(resource.metadata).lower() for resource in resources)
