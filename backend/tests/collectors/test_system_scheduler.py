from app.collectors.system_scheduler import scheduler_payload_to_resources


def test_scheduler_payload_creates_timer_and_cron_resources_without_commands():
    resources = scheduler_payload_to_resources(
        {
            "target_id": "proxmox:node:pve",
            "target_name": "pve",
            "timers": """Fri 10:00 5min Fri 09:55 5min backup.timer backup.service\n- - - - disabled.timer disabled.service\n""",
            "crontab": "@reboot secret-command --token abc\n0 2 * * * /usr/local/bin/backup",
            "cron_files": "/etc/cron.d/proxmox-backup-cron\t0 3 * * *\n/etc/cron.daily/logrotate\n",
        }
    )
    jobs = [resource for resource in resources if resource.kind.value == "cron_job"]
    assert len(jobs) == 6
    assert all("secret-command" not in str(resource.metadata) for resource in resources)
    assert any(resource.metadata.get("schedule") == "@reboot" for resource in jobs)
    assert any(resource.metadata.get("unit") == "backup.timer" for resource in jobs)
    assert any(resource.metadata.get("source_file") == "/etc/cron.d/proxmox-backup-cron" and resource.metadata.get("schedule") == "0 3 * * *" for resource in jobs)
    assert any(resource.metadata.get("source_file") == "/etc/cron.daily/logrotate" and resource.metadata.get("schedule") == "@daily" for resource in jobs)


def test_scheduler_payload_uses_stable_ids_and_maintenance_for_disabled_timer():
    resources = scheduler_payload_to_resources({
        "target_id": "proxmox:lxc:112",
        "target_name": "monitoring",
        "timers": "- - - - disabled.timer disabled.service\n",
        "crontab": "",
        "cron_files": "",
    })
    assert resources[0].id == "proxmox:lxc:112:cron:systemd"
    assert resources[2].id.endswith(":job:systemd:disabled.timer")
    assert resources[2].status.value == "maintenance"
