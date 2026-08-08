from app.collectors.proxmox_jobs import scheduled_jobs_to_resources


def test_scheduled_jobs_to_resources_normalizes_backup_and_replication():
    resources = scheduled_jobs_to_resources(
        node_id="proxmox:node:pve",
        backups=[
            {"id": "backup-1", "schedule": "Sun 02:00", "enabled": 1, "storage": "local-zfs", "node": "pve", "comment": "nightly", "password": "must-not-persist"},
        ],
        replications=[
            {"id": "replication-7", "schedule": "*/15", "disable": 1, "target": "pve2", "comment": "sync"},
        ],
    )
    assert [resource.id for resource in resources] == [
        "proxmox:node:pve:cron:backup",
        "proxmox:node:pve:cron:backup:job:backup-1",
        "proxmox:node:pve:cron:replication",
        "proxmox:node:pve:cron:replication:job:replication-7",
    ]
    assert resources[1].status.value == "up"
    assert resources[3].status.value == "maintenance"
    assert resources[1].metadata["storage"] == "local-zfs"
    assert "password" not in str(resources[1].metadata).lower()


def test_scheduled_jobs_marks_failed_last_run_degraded():
    resources = scheduled_jobs_to_resources(
        node_id="proxmox:node:pve",
        backups=[{"id": "backup-2", "enabled": 1, "last_run_status": "error"}],
        replications=[],
    )
    assert resources[1].status.value == "degraded"
