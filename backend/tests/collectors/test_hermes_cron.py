from app.collectors.hermes import profile_list_to_resources

PROFILE_OUTPUT = """Profile          Model                        Gateway      Alias        Distribution
  assistant       minimax-m2.7                running      assistant     —
  sysadmin        minimax-m2.7                running      —             —
"""

CRON_OUTPUTS = {
    "assistant": """Scheduled Jobs
  abc123 [active]
    Name:      daily-assistant-scan
    Schedule:  15 6 * * *
    Repeat:    ∞
    Next run:  2026-08-08T06:15:00+07:00
    Deliver:   local
    Skills:    google-workspace
    Last run:  2026-08-07T06:18:11+07:00  ok
    Execution: completed  run123
""",
    "sysadmin": """Scheduled Jobs
  dead456 [paused]
    Name:      broken-watchdog
    Schedule:  */15 * * * *
    Repeat:    ∞
    Next run:  None
    Deliver:   local
    Last run:  2026-08-07T06:18:11+07:00  error
""",
}


def test_profile_list_to_resources_includes_cron_hierarchy_and_safe_metadata():
    resources = profile_list_to_resources(PROFILE_OUTPUT, hostname="mac.local", cron_outputs=CRON_OUTPUTS)
    cron_resources = [resource for resource in resources if resource.kind.value in {"cron_profile", "cron_job"}]
    assert len(cron_resources) == 4
    job = next(resource for resource in cron_resources if resource.name == "daily-assistant-scan")
    assert job.id == "hermes:mac.local:profile:assistant:cron:job:abc123"
    assert job.status.value == "up"
    assert job.metadata["schedule"] == "15 6 * * *"
    paused = next(resource for resource in cron_resources if resource.name == "broken-watchdog")
    assert paused.status.value == "maintenance"
    assert "prompt" not in str(paused.metadata).lower()


def test_profile_list_to_resources_accepts_structured_prompt_summary_without_raw_prompt():
    resources = profile_list_to_resources(PROFILE_OUTPUT, hostname="mac.local", cron_outputs=CRON_OUTPUTS, cron_details={"assistant": {"abc123": {"purpose": "Membuat daily report", "scope": ["Calendar", "shared reports"], "summary_source": "hermes_job_prompt", "prompt_hash": "abc"}}})
    job = next(resource for resource in resources if resource.name == "daily-assistant-scan")
    assert job.metadata["purpose"] == "Membuat daily report"
    assert job.metadata["scope"] == ["Calendar", "shared reports"]
    assert "prompt_body" not in job.metadata
    assert "raw_prompt" not in job.metadata


def test_new_hermes_cron_is_detected_on_next_snapshot_by_stable_job_id():
    updated = dict(CRON_OUTPUTS)
    updated["assistant"] += """\n  new789 [active]\n    Name:      newly-created-job\n    Schedule:  0 12 * * *\n    Deliver:   local\n    Last run:  never\n"""
    resources = profile_list_to_resources(PROFILE_OUTPUT, hostname="mac.local", cron_outputs=updated)
    new_job = next(resource for resource in resources if resource.name == "newly-created-job")
    assert new_job.id == "hermes:mac.local:profile:assistant:cron:job:new789"
    assert new_job.status.value == "up"
