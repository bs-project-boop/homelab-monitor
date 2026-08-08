import { useEffect, useMemo, useState } from 'react'

import type { Resource, StatusEvent } from './api'
import { fetchResourceStatusEvents } from './api'
import { classifyScheduler, explainCron } from './cron'

const categoryLabels: Record<string, string> = {
  backup_recovery: 'Backup & recovery',
  security_certificates: 'Security & certificates',
  storage_maintenance: 'Storage maintenance',
  monitoring_health: 'Monitoring & health',
  system_maintenance: 'System maintenance',
  reports_delivery: 'Reports & delivery',
  unknown: 'Purpose belum teridentifikasi',
}

function metadataText(resource: Resource, key: string): string | null {
  const value = resource.metadata[key]
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function categoryFor(resource: Resource): string {
  return metadataText(resource, 'purpose_category') ?? (resource.source === 'hermes' ? 'reports_delivery' : 'unknown')
}

function statusLabel(status: Resource['status']): string {
  return status === 'up' ? 'Healthy' : status === 'degraded' ? 'Need attention' : status === 'down' ? 'Failed' : status === 'maintenance' ? 'Disabled' : 'Unknown'
}

function freshness(resource: Resource): string {
  const value = metadataText(resource, 'last_run')
  if (!value) return 'Evidence time unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Evidence time unavailable' : `Observed ${date.toLocaleString('id-ID')}`
}

function preferJob(current: Resource, candidate: Resource): Resource {
  const score = (resource: Resource) => (metadataText(resource, 'purpose_summary') ? 4 : 0) + (metadataText(resource, 'purpose_confidence') !== 'low' ? 2 : 0) + (metadataText(resource, 'schedule') !== 'unknown' ? 1 : 0)
  return score(candidate) > score(current) ? candidate : current
}

function deduplicateJobs(resources: Resource[]): Resource[] {
  const unique = new Map<string, Resource>()
  for (const resource of resources) {
    const identity = metadataText(resource, 'source_file') ?? metadataText(resource, 'unit') ?? resource.name.replace(/ entry \d+$/, '')
    const key = `${resource.parent_id ?? 'root'}:${resource.source}:${identity}`
    unique.set(key, unique.has(key) ? preferJob(unique.get(key)!, resource) : resource)
  }
  return [...unique.values()]
}

export function ExecutiveSchedulerPanel({ resources, error }: { resources: Resource[]; error: boolean }) {
  const jobs = useMemo(() => deduplicateJobs(resources.filter((resource) => resource.kind === 'cron_job' && ['hermes_profile', 'docker_worker', 'system_scheduler'].includes(classifyScheduler(resource, resources)))), [resources])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [runHistory, setRunHistory] = useState<StatusEvent[]>([])
  const selected = jobs.find((job) => job.id === selectedId) ?? jobs[0] ?? null
  const groups = useMemo(() => {
    const grouped = new Map<string, Resource[]>()
    for (const job of jobs) {
      const category = categoryFor(job)
      grouped.set(category, [...(grouped.get(category) ?? []), job])
    }
    return [...grouped.entries()].sort(([leftCategory, left], [rightCategory, right]) => {
      const attention = (items: Resource[]) => items.filter((item) => ['degraded', 'down', 'unknown'].includes(item.status)).length
      return attention(right) - attention(left) || (categoryLabels[leftCategory] ?? leftCategory).localeCompare(categoryLabels[rightCategory] ?? rightCategory)
    })
  }, [jobs])
  const attention = jobs.filter((job) => ['degraded', 'down', 'unknown'].includes(job.status))
  const purposeReview = jobs.filter((job) => metadataText(job, 'purpose_confidence') === 'low' || !metadataText(job, 'purpose_summary'))
  const counts = {
    total: jobs.length,
    healthy: jobs.filter((job) => job.status === 'up').length,
    attention: attention.length,
    purposeReview: purposeReview.length,
    disabled: jobs.filter((job) => job.status === 'maintenance').length,
  }
  const explanation = selected ? explainCron(selected, resources) : null

  useEffect(() => {
    if (selectedId && jobs.some((job) => job.id === selectedId)) return
    setSelectedId(jobs[0]?.id ?? null)
  }, [jobs, selectedId])

  useEffect(() => {
    if (!selected) {
      setRunHistory([])
      return
    }
    let cancelled = false
    fetchResourceStatusEvents(selected.id).then((response) => { if (!cancelled) setRunHistory(response.data) }).catch(() => { if (!cancelled) setRunHistory([]) })
    return () => { cancelled = true }
  }, [selected?.id])

  if (error) return <section className="panel executive-cron" aria-labelledby="executive-cron-title"><p className="muted" role="status">Cron inventory is temporarily unavailable.</p></section>

  return <section className="panel executive-cron" aria-labelledby="executive-cron-title">
    <div className="panel-heading executive-cron-heading">
      <div><p className="eyebrow">SCHEDULED WORK · EXECUTIVE VIEW</p><h3 id="executive-cron-title">What runs automatically?</h3><p className="panel-subtitle">Ringkasan fungsi dan risiko pekerjaan terjadwal. Detail teknis tetap tersedia saat sebuah pekerjaan dipilih.</p></div>
      <span className="label">{jobs.length} jobs</span>
    </div>

    <div className="cron-summary-grid" aria-label="Scheduled work summary">
      <div className="cron-summary-card healthy"><strong>{counts.healthy}</strong><span>Healthy</span></div>
      <div className="cron-summary-card attention"><strong>{counts.attention}</strong><span>Need attention</span></div>
      <div className="cron-summary-card unknown"><strong>{counts.purposeReview}</strong><span>Purpose needs review</span></div>
      <div className="cron-summary-card disabled"><strong>{counts.disabled}</strong><span>Disabled</span></div>
    </div>

    <div className="cron-executive-insight" role="status">
      {attention.length ? <><strong>{attention.length} scheduled job perlu perhatian.</strong><span>Periksa group yang ditandai dan pilih job untuk melihat dampak jika gagal.</span></> : <><strong>Semua scheduled job terpantau sehat.</strong><span>Tetap tinjau job dengan confidence rendah untuk melengkapi dokumentasi fungsi.</span></>}
    </div>

    <div className="cron-executive-layout">
      <div className="cron-purpose-groups" aria-label="Scheduled work by purpose">
        <div className="cron-section-label">GROUP BERDASARKAN FUNGSI</div>
        {groups.map(([category, group]) => {
          const groupAttention = group.filter((job) => ['degraded', 'down', 'unknown'].includes(job.status)).length
          const open = expandedCategory === category || (!expandedCategory && group.some((job) => job.id === selected?.id))
          return <section className={`cron-purpose-group ${groupAttention ? 'has-attention' : ''}`} key={category}>
            <button type="button" className="cron-purpose-heading" aria-expanded={open} onClick={() => setExpandedCategory(open ? null : category)}>
              <span><strong>{categoryLabels[category] ?? category}</strong><small>{group.length} jobs · {group.length - groupAttention} healthy{groupAttention ? ` · ${groupAttention} perlu perhatian` : ''}</small></span><b>{open ? '−' : '+'}</b>
            </button>
            {open && <div className="cron-purpose-list">{group.slice(0, 12).map((job) => <button type="button" className={`cron-executive-row ${selected?.id === job.id ? 'selected' : ''}`} key={job.id} onClick={() => setSelectedId(job.id)}><span className={`cron-status-dot ${job.status}`} aria-hidden="true" /><span><strong>{metadataText(job, 'purpose_title') ?? job.name}</strong><small>{job.name} · {job.source} · {statusLabel(job.status)}</small></span><b>{statusLabel(job.status)}</b></button>)}{group.length > 12 && <small className="cron-group-foot">Showing 12 of {group.length}; use search in the technical view for the remainder.</small>}</div>}
          </section>
        })}
      </div>

      {selected && explanation && <article className="cron-executive-detail" aria-live="polite">
        <div className="cron-detail-kicker">SELECTED WORK</div>
        <h4>{metadataText(selected, 'purpose_title') ?? selected.name}</h4>
        <p className="cron-detail-summary">{metadataText(selected, 'purpose_summary') ?? explanation.purpose}</p>
        <div className="cron-detail-confidence">Confidence: {metadataText(selected, 'purpose_confidence') ?? 'inferred'} · {freshness(selected)}</div>
        <dl className="cron-detail-facts"><div><dt>Melakukan apa?</dt><dd>{metadataText(selected, 'purpose_summary') ?? explanation.purpose}</dd></div><div><dt>Dijalankan oleh?</dt><dd>{explanation.executor}</dd></div><div><dt>Kapan?</dt><dd>{explanation.schedule}</dd></div><div><dt>Jika gagal?</dt><dd>{metadataText(selected, 'impact_if_failed') ?? explanation.ifFails}</dd></div></dl>
        <details className="technical-detail"><summary>Lihat technical evidence</summary><p>{selected.source} · {selected.name}</p><code>{selected.id}</code><p>Parent: {selected.parent_id ?? 'root'}</p></details>
        <section className="cron-history" aria-label="Run history"><div><strong>Riwayat status</strong><span>{runHistory.length} event</span></div>{runHistory.length ? runHistory.slice(0, 5).map((event) => <p key={event.id}><time dateTime={event.observed_at}>{new Date(event.observed_at).toLocaleString('id-ID')}</time><b className={event.status}>{event.status}</b>{event.reason}</p>) : <small>Belum ada perubahan status yang tercatat.</small>}</section>
      </article>}
    </div>
  </section>
}
