import hashlib
import re
from typing import Any

from app.domain.resource import Resource, ResourceKind
from app.domain.status import Status


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")[:120] or "unknown"


def _cron_schedule(line: str) -> str:
    fields = line.split()
    if fields and fields[0].startswith("@"):
        return fields[0][:40]
    return " ".join(fields[:5])[:80] if len(fields) >= 5 else "unknown"


def _cron_purpose(source: str, line: str) -> dict[str, object]:
    identity = f"{source} {line}".lower()
    mappings = (
        (("certbot",), "security_certificates", "Certificate renewal", "Memeriksa dan memperbarui sertifikat TLS yang dikelola Certbot.", "HTTPS dapat terganggu setelah sertifikat lama kedaluwarsa.", "high"),
        (("logrotate",), "system_maintenance", "Log rotation", "Merotasi dan membersihkan log lama agar penggunaan disk tetap terkendali.", "Log dapat memenuhi disk dan menyulitkan investigasi jika tidak dirotasi.", "high"),
        (("e2scrub",), "storage_maintenance", "Filesystem metadata maintenance", "Memeriksa metadata filesystem secara berkala untuk mendeteksi masalah pada storage.", "Masalah metadata storage dapat terlambat terdeteksi.", "medium"),
        (("fstrim",), "storage_maintenance", "SSD discard maintenance", "Memberi tahu storage yang didukung bahwa blok yang tidak terpakai dapat dibuang.", "Efisiensi discard storage dapat menurun; ini bukan backup data.", "high"),
        (("dpkg-db-backup",), "backup_recovery", "Package database backup", "Membuat salinan database package manager untuk membantu pemulihan metadata paket.", "Pemulihan metadata paket menjadi lebih sulit jika database rusak.", "high"),
        (("anacron",), "system_maintenance", "Deferred periodic jobs", "Menjalankan pekerjaan periodik yang belum sempat berjalan pada jadwal sebelumnya.", "Pekerjaan maintenance periodik dapat tertunda.", "high"),
        (("smart",), "monitoring_health", "Disk health monitoring", "Memeriksa indikator kesehatan disk dan memberi sinyal jika ada gejala kegagalan.", "Peringatan kesehatan disk dapat terlambat.", "high"),
        (("rsync",), "backup_recovery", "Data synchronization", "Menyinkronkan file dari sumber ke target yang ditentukan.", "Salinan target dapat tertinggal dari sumber.", "medium"),
    )
    for tokens, category, title, summary, impact, confidence in mappings:
        if any(token in identity for token in tokens):
            return {"purpose_category": category, "purpose_title": title, "purpose_summary": summary, "impact_if_failed": impact, "purpose_confidence": confidence}
    return {"purpose_category": "unknown", "purpose_title": "Purpose belum teridentifikasi", "purpose_summary": f"Entry terjadwal dari {source}; tindakan spesifik belum dapat dibuktikan dari metadata aman yang tersedia.", "impact_if_failed": "Dampak spesifik belum dapat dipastikan tanpa evidence command/service yang lebih lengkap.", "purpose_confidence": "low"}


def _timer_job(group_id: str, fields: list[str]) -> Resource | None:
    if len(fields) < 2 or not fields[-2].endswith(".timer"):
        return None
    unit = fields[-2]
    service = fields[-1]
    disabled = fields[0] == "-" and fields[1] == "-"
    purpose = _cron_purpose(unit, service)
    return Resource(
        id=f"{group_id}:job:systemd:{_slug(unit)}",
        kind=ResourceKind.CRON_JOB,
        name=unit,
        source="systemd",
        status=Status.MAINTENANCE if disabled else Status.UP,
        parent_id=group_id,
        metadata={
            "scheduler": "systemd",
            "unit": unit,
            "service": service,
            "next": fields[0][:80],
            "last": fields[3][:80] if len(fields) > 3 else "-",
            "purpose": f"Menjalankan service systemd {service} berdasarkan timer {unit}.",
            "scope": [unit, service],
            "summary_source": "systemd timer/service evidence",
            **purpose,
        },
    )


def _cron_file_schedule(entry: str) -> tuple[str, str]:
    source, separator, schedule = entry.partition("\t")
    source = source.strip()
    if separator and schedule.strip():
        return source, schedule.strip()
    for folder, label in (("cron.hourly", "@hourly"), ("cron.daily", "@daily"), ("cron.weekly", "@weekly"), ("cron.monthly", "@monthly")):
        if source.startswith(f"/etc/{folder}/"):
            return source, label
    return source, "unknown"


def _cron_job(group_id: str, line: str, source: str, index: int) -> Resource:
    digest = hashlib.sha256(line.encode("utf-8", "replace")).hexdigest()[:12]
    purpose_details = _cron_purpose(source, line)
    return Resource(
        id=f"{group_id}:job:cron:{_slug(source)}:{digest}:{index}",
        kind=ResourceKind.CRON_JOB,
        name=f"{source} entry {index}",
        source="cron",
        status=Status.UP,
        parent_id=group_id,
        metadata={"scheduler": "cron", "schedule": _cron_schedule(line), "source_file": source[:240], "summary_source": "cron file schedule evidence", **purpose_details},
    )


def scheduler_payload_to_resources(payload: dict[str, Any]) -> list[Resource]:
    target_id = str(payload["target_id"])
    timers_group = f"{target_id}:cron:systemd"
    cron_group = f"{target_id}:cron:cron"
    resources: list[Resource] = [
        Resource(id=timers_group, kind=ResourceKind.CRON_PROFILE, name=f"{payload['target_name']} systemd timers", source="systemd", status=Status.UP, parent_id=target_id, metadata={"scheduler": "systemd"}),
        Resource(id=cron_group, kind=ResourceKind.CRON_PROFILE, name=f"{payload['target_name']} cron", source="cron", status=Status.UP, parent_id=target_id, metadata={"scheduler": "cron"}),
    ]
    for raw_line in str(payload.get("timers", "")).splitlines():
        job = _timer_job(timers_group, raw_line.split())
        if job is not None:
            resources.append(job)
    cron_index = 0
    for raw_line in str(payload.get("crontab", "")).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("SHELL=") or line.startswith("PATH="):
            continue
        cron_index += 1
        resources.append(_cron_job(cron_group, line, "user-crontab", cron_index))
    for entry in str(payload.get("cron_files", "")).splitlines():
        entry = entry.strip()
        if not entry:
            continue
        path, schedule = _cron_file_schedule(entry)
        if not path or path.endswith("/.placeholder"):
            continue
        cron_index += 1
        resources.append(_cron_job(cron_group, schedule, path, cron_index))
    resources[0].metadata["job_count"] = sum(resource.parent_id == timers_group and resource.kind == ResourceKind.CRON_JOB for resource in resources)
    resources[1].metadata["job_count"] = sum(resource.parent_id == cron_group and resource.kind == ResourceKind.CRON_JOB for resource in resources)
    return resources
