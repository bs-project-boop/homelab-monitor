import { useEffect, useRef, useState } from 'react'

import { createAccessSession, fetchAutomationOutputs, fetchIncidents, fetchLogs, fetchOverview, fetchResources, fetchResourceStatusEvents, fetchStatusEvents, fetchVersions, revokeAccessSession, type AccessSession, type AutomationOutput, type Incident, type LogEntry, type MonitorStatus, type OverviewData, type Resource, type StatusEvent } from './api'
import { classifyScheduler, explainCron, type CronExplanation } from './cron'
import { sortByStatusThenName, statusLabel, versionInfo, type UpdateState } from './inventory'

const statusLabels: Array<{ key: MonitorStatus; label: string }> = [
  { key: 'up', label: 'Up' },
  { key: 'degraded', label: 'Degraded' },
  { key: 'down', label: 'Down' },
  { key: 'unknown', label: 'Unknown' },
]

function StatusList({ data }: { data: OverviewData }) {
  return (
    <div className="status-list" aria-label="Resource status counts">
      {statusLabels.map(({ key, label }) => (
        <div className={`status-row ${key}`} key={key}>
          <span className="status-name"><i aria-hidden="true" />{label}</span>
          <strong>{data.status_counts[key] ?? 0}</strong>
        </div>
      ))}
    </div>
  )
}

function TransitionTimeline({ events }: { events: StatusEvent[] }) {
  return (
    <section className="panel timeline-panel" aria-label="Recent status transitions">
      <div className="panel-heading"><div><p className="eyebrow">HISTORY</p><h3>Recent transitions</h3></div><span className="label">Last {events.length}</span></div>
      {events.length ? <div className="timeline-list">
        {events.map((event) => (
          <div className="timeline-item" key={event.id}>
            <span className={`timeline-dot ${event.status}`} aria-hidden="true" />
            <div className="timeline-copy"><strong>{event.resource_id}</strong><span>{event.reason}</span></div>
            <div className="timeline-meta"><b className={event.status}>{event.status}</b><time dateTime={event.observed_at}>{new Date(event.observed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div>
          </div>
        ))}
      </div> : <p className="muted empty-history">No status transitions observed yet.</p>}
    </section>
  )
}

function IncidentPanel({ incidents, error }: { incidents: Incident[]; error: boolean }) {
  return (
    <section className="panel incidents-panel" aria-labelledby="incidents-title" aria-live="polite">
      <div className="panel-heading">
        <div><p className="eyebrow">ATTENTION</p><h3 id="incidents-title">Open incidents</h3></div>
        <span className="incident-count" aria-label={`${incidents.length} open incidents`}>{incidents.length}</span>
      </div>
      {error ? <p className="muted incident-empty">Incident data is temporarily unavailable.</p> : incidents.length ? <div className="incident-list">
        {incidents.map((incident) => (
          <article className="incident-item" key={incident.id}>
            <span className={`incident-marker ${incident.severity}`} aria-hidden="true" />
            <div className="incident-copy"><strong>{incident.title}</strong><span>{incident.resource_id}</span></div>
            <div className="incident-meta"><b className={incident.severity}>{incident.severity}</b><time dateTime={incident.last_seen_at}>{new Date(incident.last_seen_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div>
          </article>
        ))}
      </div> : <p className="muted incident-empty">No open incidents observed.</p>}
    </section>
  )
}

function Highlight({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig'))
  return <>{parts.map((part, index) => part.toLowerCase() === query.toLowerCase() ? <mark key={`${part}-${index}`}>{part}</mark> : part)}</>
}

function freshnessLabel(value: unknown): string {
  if (typeof value !== 'string') return 'Checked time unavailable'
  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp)) return 'Checked time unavailable'
  const minutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000))
  return minutes < 1 ? 'Checked just now' : `Checked ${minutes}m ago`
}

function SchedulerPanel({ resources, error }: { resources: Resource[]; error: boolean }) {
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [sort, setSort] = useState('name')
  const [profile, setProfile] = useState('all')
  const [showSystem, setShowSystem] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const profiles = resources.filter((resource) => resource.kind === 'cron_profile' && resource.source === 'hermes' && resources.some((owner) => owner.id === resource.parent_id && owner.kind === 'hermes_profile'))
  const jobs = resources.filter((resource) => classifyScheduler(resource, resources) === 'hermes_profile')
  const workers = resources.filter((resource) => classifyScheduler(resource, resources) === 'docker_worker')
  const systemJobs = resources.filter((resource) => classifyScheduler(resource, resources) === 'system_scheduler')
  const unresolvedJobs = resources.filter((resource) => classifyScheduler(resource, resources) === 'hermes_unresolved')
  const allRows = showSystem ? [...jobs, ...workers, ...systemJobs] : [...jobs, ...workers]
  const profileOptions = profiles.map((cronProfile) => resources.find((resource) => resource.id === cronProfile.parent_id)).filter((owner): owner is Resource => Boolean(owner))
  const filteredRows = allRows.filter((job) => {
    const parent = job.parent_id ? resources.find((resource) => resource.id === job.parent_id) : null
    const owner = parent?.parent_id ? resources.find((resource) => resource.id === parent.parent_id) : null
    const haystack = `${job.name} ${job.id} ${job.source} ${parent?.name ?? ''} ${owner?.name ?? ''} ${job.metadata.schedule ?? ''}`.toLowerCase()
    return (profile === 'all' || owner?.id === profile || (profile === 'docker' && job.source === 'docker')) && (status === 'all' || job.status === status) && haystack.includes(query.toLowerCase())
  }).sort((left, right) => {
    if (sort === 'status') return left.status.localeCompare(right.status) || left.name.localeCompare(right.name)
    if (sort === 'host') return String(left.metadata.host ?? left.parent_id ?? '').localeCompare(String(right.metadata.host ?? right.parent_id ?? '')) || left.name.localeCompare(right.name)
    return left.name.localeCompare(right.name)
  })
  const rows = filteredRows.slice(0, page * 10)
  useEffect(() => {
    if (!selectedId && rows[0]) setSelectedId(rows[0].id)
    if (selectedId && !allRows.some((job) => job.id === selectedId)) setSelectedId(rows[0]?.id ?? null)
  }, [selectedId, rows, allRows])
  const selected = selectedId ? allRows.find((job) => job.id === selectedId) : null
  const explanation: CronExplanation | null = selected ? explainCron(selected, resources) : null
  const [runHistory, setRunHistory] = useState<StatusEvent[]>([])
  const [runHistoryError, setRunHistoryError] = useState(false)
  useEffect(() => {
    let cancelled = false
    if (!selectedId) { setRunHistory([]); return () => { cancelled = true } }
    setRunHistoryError(false)
    fetchResourceStatusEvents(selectedId).then((response) => { if (!cancelled) setRunHistory(response.data) }).catch(() => { if (!cancelled) setRunHistoryError(true) })
    return () => { cancelled = true }
  }, [selectedId])
  const clearFilters = () => { setQuery(''); setStatus('all'); setProfile('all'); setSort('name'); setPage(1) }
  return <section className="panel scheduler-panel" aria-labelledby="scheduler-title">
    <div className="panel-heading"><div><p className="eyebrow">HUMAN-MANAGED SCHEDULED WORK</p><h3 id="scheduler-title">Hermes profiles & workers</h3><p className="panel-subtitle">System/OS cron tidak ditampilkan di daftar ini agar fokus tetap pada automation yang dikelola profile dan worker.</p></div><span className="label">{profiles.length} Hermes profiles · {allRows.length} jobs/workers</span></div>
    {error ? <p className="muted" role="status">Scheduler inventory is temporarily unavailable.</p> : <>
      <div className="scheduler-profile-list" aria-label="Scheduler profiles">{profiles.slice(0, 8).map((profileResource) => { const rawCount = Number(profileResource.metadata.job_count); const jobCount = Number.isFinite(rawCount) ? rawCount : null; const owner = resources.find((resource) => resource.id === profileResource.parent_id); return <button type="button" className={`scheduler-profile ${profile === owner?.id ? 'selected' : ''}`} key={profileResource.id} onClick={() => { if (owner) { setProfile(owner.id); setPage(1) } }}><span className="scheduler-kind">{profileResource.source}</span><strong>{owner?.name ?? profileResource.name}</strong><span className="muted">{jobCount === null ? '—' : jobCount} jobs</span></button> })}</div>
      <div className="scheduler-toolbar"><label><span className="sr-only">Search scheduled jobs</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1) }} placeholder="Search job, host, or path…" /></label><label><span className="sr-only">Filter managed profile</span><select value={profile} onChange={(event) => { setProfile(event.target.value); setPage(1) }}><option value="all">All managed profiles</option>{profileOptions.map((owner) => <option value={owner.id} key={owner.id}>Profile: {owner.name}</option>)}<option value="docker">Docker workers</option></select></label><label><span className="sr-only">Filter job status</span><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="all">All statuses</option><option value="up">Up</option><option value="degraded">Degraded</option><option value="down">Down</option></select></label><label><span className="sr-only">Sort scheduled jobs</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="name">Sort: name</option><option value="host">Sort: host</option><option value="status">Sort: status</option></select></label><button type="button" className="clear-filter-button" onClick={clearFilters}>Clear filters</button><button type="button" className="clear-filter-button" aria-pressed={showSystem} onClick={() => { setShowSystem((value) => !value); setSelectedId(null); setPage(1) }}>{showSystem ? 'Hide system schedulers' : 'Show all schedulers'}</button></div>
      <div className="scheduler-boundary-note" role="note"><strong>Not shown by default:</strong> {systemJobs.length} system/OS/Proxmox cron entries{unresolvedJobs.length ? ` · ${unresolvedJobs.length} Hermes entries need provenance review` : ''}. Docker workers ({workers.length}) remain visible because they represent workload automation, not host maintenance.</div>
      <div className="scheduler-job-list" aria-label="Hermes profile jobs and Docker workers">{rows.map((job) => { const parent = job.parent_id ? resources.find((resource) => resource.id === job.parent_id) : null; const schedule = typeof job.metadata.schedule === 'string' && job.metadata.schedule.toLowerCase() !== 'unknown' ? job.metadata.schedule : typeof job.metadata.unit === 'string' ? job.metadata.unit : null; const badge = typeof job.metadata.execution_mode === 'string' ? job.metadata.execution_mode : classifyScheduler(job, resources) === 'system_scheduler' ? 'system scheduler' : job.source === 'docker' ? 'docker worker' : 'Hermes job'; const purposeState = typeof job.metadata.purpose === 'string' ? 'summary current' : 'summary fallback'; return <button className={`scheduler-job ${selectedId === job.id ? 'selected' : ''}`} key={job.id} type="button" onClick={() => setSelectedId(job.id)}><span className={`scheduler-status ${job.status}`} aria-hidden="true" /><span><strong><Highlight text={job.name} query={query} /></strong><span>{[parent?.name, schedule].filter(Boolean).join(' · ') || `${job.source} scheduled job`}</span><small className="scheduler-job-badges"><i>{badge}</i><i>{purposeState}</i></small></span><b className={job.status}>{job.status}</b></button> })}</div>
      {!rows.length && <p className="muted">No scheduled work matches the current filters.</p>}
      {selected && explanation && <article className="scheduler-detail human-detail" aria-live="polite"><div className="detail-hero"><p className="eyebrow">APA FUNGSI CRON INI?</p><h4>{selected.name}</h4><p className="detail-lead">{explanation.purpose}</p><p className="detail-basis">{explanation.purposeBasis}</p></div><div className="plain-language-grid"><div><dt>Siapa yang mengelola?</dt><dd><strong>{explanation.owner}</strong><span>{explanation.ownerDetail}</span></dd></div><div><dt>Apa yang menjalankan?</dt><dd><strong>{explanation.executor}</strong><span>{explanation.target}</span></dd></div><div><dt>Scope dan tujuannya?</dt><dd><span>{explanation.why}</span></dd></div><div><dt>Jika gagal apa dampaknya?</dt><dd><span>{explanation.ifFails}</span></dd></div></div><dl className="scheduler-facts"><div><dt>Jadwal</dt><dd>{explanation.schedule}</dd></div><div><dt>Status</dt><dd className={selected.status}>{explanation.state}</dd></div><div><dt>Delivery</dt><dd>{explanation.delivery}</dd></div><div><dt>Evidence</dt><dd>{freshnessLabel(selected.metadata.last_run)}</dd></div></dl><details className="technical-detail"><summary>Technical detail</summary><code>{selected.id}</code><p>{selected.source} · parent: {selected.parent_id ?? 'root'}</p></details><section className="scheduler-run-history" aria-label="Run history"><div className="detail-section-heading"><strong>Riwayat perubahan status</strong><span>{runHistoryError ? 'Tidak tersedia' : `${runHistory.length} event`}</span></div>{runHistory.length ? <div>{runHistory.slice(0, 8).map((event) => <div className="scheduler-run" key={event.id}><time dateTime={event.observed_at}>{new Date(event.observed_at).toLocaleString('id-ID')}</time><b className={event.status}>{event.status}</b><span>{event.reason}</span></div>)}</div> : <p className="muted">Belum ada perubahan status yang tercatat.</p>}</section></article>}
      <div className="scheduler-pagination"><span className="scheduler-foot muted">Showing {rows.length} of {filteredRows.length} filtered · {allRows.length} total</span>{filteredRows.length > rows.length && <button type="button" className="refresh-button" onClick={() => setPage((current) => current + 1)}>Load more</button>}</div>
    </>}
  </section>
}


function ResourceExplorer({ resources, selectedId, onSelect, logs, logsLoading, logsError }: { resources: Resource[]; selectedId: string | null; onSelect: (id: string) => void; logs: LogEntry[]; logsLoading: boolean; logsError: boolean }) {
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState('all')
  const [status, setStatus] = useState('all')
  const selected = resources.find((resource) => resource.id === selectedId) ?? null
  const parent = selected?.parent_id ? resources.find((resource) => resource.id === selected.parent_id) : null
  const filtered = resources.filter((resource) => {
    const haystack = `${resource.name} ${resource.id} ${resource.kind} ${resource.source}`.toLowerCase()
    return haystack.includes(query.toLowerCase()) && (kind === 'all' || resource.kind === kind) && (status === 'all' || resource.status === status)
  }).slice(0, 80)
  const metadataEntries = selected ? Object.entries(selected.metadata).filter(([, value]) => value !== null && value !== undefined && value !== '') : []
  return (
    <section className="resource-explorer" aria-labelledby="resource-explorer-title">
      <div className="panel-heading explorer-heading"><div><p className="eyebrow">DRILL-DOWN</p><h3 id="resource-explorer-title">Resource explorer</h3><p className="muted">Select a target to inspect identity, evidence, and recent logs.</p></div><span className="label">{resources.length} resources</span></div>
      <div className="explorer-controls">
        <label className="search-field"><span className="sr-only">Search resources</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, ID, source…" /></label>
        <label><span className="sr-only">Filter kind</span><select value={kind} onChange={(event) => setKind(event.target.value)}><option value="all">All kinds</option>{Array.from(new Set(resources.map((resource) => resource.kind))).sort().map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label><span className="sr-only">Filter status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All status</option>{statusLabels.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}</select></label>
      </div>
      <div className="explorer-layout">
        <div className="resource-list" aria-label="Filtered resources">
          {filtered.map((resource) => <button className={`resource-row ${resource.id === selectedId ? 'selected' : ''}`} key={resource.id} type="button" onClick={() => onSelect(resource.id)}><span className={`resource-dot ${resource.status}`} aria-hidden="true" /><span className="resource-row-copy"><strong>{resource.name}</strong><small>{resource.kind} · {resource.source}</small></span><b className={resource.status}>{resource.status}</b></button>)}
          {!filtered.length && <p className="muted explorer-empty">No resources match the current filters.</p>}
          {filtered.length < resources.filter((resource) => `${resource.name} ${resource.id} ${resource.kind} ${resource.source}`.toLowerCase().includes(query.toLowerCase())).length && <p className="muted explorer-foot">Showing first {filtered.length} matches.</p>}
        </div>
        <article className="resource-detail" aria-live="polite">
          {!selected ? <p className="muted">Choose a resource to inspect details.</p> : <>
            <div className="detail-title"><div><p className="eyebrow">SELECTED RESOURCE</p><h4>{selected.name}</h4><code>{selected.id}</code></div><span className={`detail-status ${selected.status}`}>{selected.status}</span></div>
            <dl className="detail-facts"><div><dt>Kind</dt><dd>{selected.kind}</dd></div><div><dt>Source</dt><dd>{selected.source}</dd></div><div><dt>Parent</dt><dd>{parent?.name ?? selected.parent_id ?? 'Root resource'}</dd></div></dl>
            {metadataEntries.length > 0 && <div className="metadata-block"><p className="label">Evidence metadata</p><dl>{metadataEntries.slice(0, 12).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl></div>}
            <div className="logs-block"><div className="panel-heading"><div><p className="eyebrow">EVIDENCE</p><h5>Recent logs</h5></div><span className="label">{logs.length}</span></div>{logsLoading ? <p className="muted">Loading logs…</p> : logsError ? <p className="muted" role="status">Logs are temporarily unavailable.</p> : logs.length ? <div className="log-list">{logs.map((log) => <article className="log-row" key={log.id}><div className="log-meta"><b className={`log-level ${log.level}`}>{log.level}</b><span>{log.source}</span><time dateTime={log.observed_at}>{new Date(log.observed_at).toLocaleString()}</time></div><p>{log.message}</p></article>)}</div> : <p className="muted">No logs recorded for this resource.</p>}</div>
          </>}
        </article>
      </div>
    </section>
  )
}

function AccessConsole({ resources }: { resources: Resource[] }) {
  const [token, setToken] = useState('')
  const [target, setTarget] = useState('pve')
  const [mode, setMode] = useState<'logs' | 'shell'>('logs')
  const [session, setSession] = useState<AccessSession | null>(null)
  const [output, setOutput] = useState('')
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const targets = [{ id: 'pve', label: 'Proxmox node' }, ...resources.filter((resource) => resource.kind === 'lxc').map((resource) => { const vmid = resource.metadata.vmid ?? resource.id.match(/(?:lxc|ct)[:/-](\d+)/)?.[1] ?? resource.name; return { id: `lxc-${vmid}`, label: `LXC ${vmid} · ${resource.name}` } }), { id: 'worker-recyclarr', label: 'Docker worker · recyclarr' }, { id: 'worker-unpackerr', label: 'Docker worker · unpackerr' }]
  const canShell = target === 'pve' || target.startsWith('lxc-')

  const socketRef = useRef<WebSocket | null>(null)
  useEffect(() => {
    if (!session || !token) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/access/sessions/${session.session_id}/stream`, ['homelab-operator', token])
    socketRef.current = socket
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { type?: string; data?: string; error?: string }
        if (message.type === 'output') setOutput((current) => `${current}${message.data ?? ''}`.slice(-120000))
        if (message.type === 'error') setError(message.error ?? 'Access relay error')
        if (message.type === 'ready') setOutput((current) => `${current}\n[session ready: ${session.target}/${session.mode}]\n`)
        if (message.type === 'closed') setOutput((current) => `${current}\n[session closed]\n`)
      } catch {
        setOutput((current) => `${current}${event.data}`.slice(-120000))
      }
    }
    socket.onerror = () => setError('Access WebSocket unavailable')
    socket.onclose = () => setBusy(false)
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [session, token])

  const open = async () => {
    if (!token.trim()) { setError('Operator token is required'); return }
    setBusy(true); setError(null); setOutput('')
    try { setSession(await createAccessSession(target, mode, token.trim())) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to open access session'); setBusy(false) }
  }
  const close = async () => {
    if (session) await revokeAccessSession(session.session_id, token).catch(() => undefined)
    setSession(null); setBusy(false); setOutput((current) => `${current}\n[session revoked]\n`)
  }
  const sendInput = () => {
    if (!session || !input || socketRef.current?.readyState !== WebSocket.OPEN) return
    socketRef.current.send(JSON.stringify({ type: 'input', data: `${input}\n` }))
    setInput('')
  }
  return (
    <section className="access-console" aria-labelledby="access-console-title">
      <div className="panel-heading"><div><p className="eyebrow">CONTROLLED ACCESS</p><h3 id="access-console-title">Live logs & SSH console</h3><p className="muted">Authenticated, allowlisted, audited, and time-limited.</p></div><span className={`access-state ${session ? 'active' : ''}`}>{session ? 'Session active' : 'No session'}</span></div>
      <div className="access-controls"><label><span className="label">Operator token</span><input type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="Enter one-time operator token" autoComplete="off" disabled={Boolean(session)} /></label><label><span className="label">Target</span><select value={target} onChange={(event) => { setTarget(event.target.value); if (event.target.value.startsWith('worker-')) setMode('logs') }} disabled={Boolean(session)}>{targets.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label><span className="label">Mode</span><select value={mode} onChange={(event) => setMode(event.target.value as 'logs' | 'shell')} disabled={Boolean(session) || !canShell}><option value="logs">Read-only live logs</option><option value="shell">Interactive SSH console</option></select></label>{session ? <button type="button" className="danger-button" onClick={() => void close()}>Revoke session</button> : <button type="button" className="refresh-button" onClick={() => void open()} disabled={busy}>{busy ? 'Opening…' : 'Open session'}</button>}</div>
      {error && <p className="access-error" role="alert">{error}</p>}
      <pre className="terminal-output" aria-label="Live access output">{output || 'Session output will appear here. Read-only logs are the default.'}</pre>
      {session?.mode === 'shell' && <form className="terminal-input" onSubmit={(event) => { event.preventDefault(); sendInput() }}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Type command/input; session is audited" autoComplete="off" /><button type="submit" className="refresh-button">Send</button></form>}
    </section>
  )
}

type TabKey = 'overview' | 'servers' | 'cron' | 'logs' | 'outputs'

function CollectorPulse({ events, latestStatus }: { events: StatusEvent[]; latestStatus?: string }) {
  const observed = events.slice(0, 24).map((event) => event.status)
  const ticks = Array.from({ length: 24 }, (_, index) => observed[index] ?? 'unknown')
  return <section className="pulse-card" aria-label="Recent collector evidence"><div className="pulse-head"><span className="pulse-label">Collector evidence · recent observations</span><div className="pulse-legend"><span><i className="pulse-up" />up</span><span><i className="pulse-warn" />degraded</span><span><i className="pulse-unknown" />no data</span></div></div><div className="pulse-strip">{ticks.map((status, index) => <span className={`pulse-tick ${status}`} key={`${status}-${index}`} style={{ height: `${Math.max(28, 35 + ((index * 17) % 65))}%` }} title={`${status} · observation ${index + 1}`} />)}</div><div className="pulse-foot"><span>Recent transitions</span><span>{latestStatus ? `Latest collector: ${latestStatus}` : 'Waiting for collector'}</span></div></section>
}


function TabNav({ active, onChange }: { active: TabKey; onChange: (tab: TabKey) => void }) {
  const tabs: Array<{ id: TabKey; label: string; description: string }> = [
    { id: 'overview', label: 'Overview', description: 'Summary and incidents' },
    { id: 'servers', label: 'Servers & Apps', description: 'Runtime inventory and versions' },
    { id: 'cron', label: 'Cron', description: 'Scheduled work' },
    { id: 'logs', label: 'Logs', description: 'Normalized and live evidence' },
    { id: 'outputs', label: 'Artifacts & Delivery', description: 'Reports, GitHub, Discord' },
  ]
  return <nav className="tab-nav" aria-label="Monitoring sections" role="tablist">{tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={active === tab.id} aria-controls={`${tab.id}-panel`} className={`tab-button ${active === tab.id ? 'active' : ''}`} onClick={() => onChange(tab.id)}><strong>{tab.label}</strong><span>{tab.description}</span></button>)}</nav>
}

function VersionBadge({ state }: { state: UpdateState }) {
  const labels: Record<UpdateState, string> = { up_to_date: 'Up to date', update_available: 'Update available', unknown: 'Version unknown' }
  return <span className={`version-badge ${state}`}>{labels[state]}</span>
}

function InventoryRow({ resource, resources }: { resource: Resource; resources: Resource[] }) {
  const version = versionInfo(resource)
  const parent = resource.parent_id ? resources.find((item) => item.id === resource.parent_id) : null
  const metadata = resource.metadata
  const runtime = typeof metadata.image === 'string' ? metadata.image : typeof metadata.lifecycle_status === 'string' ? metadata.lifecycle_status : resource.source
  const detail = [parent?.name, typeof metadata.ports === 'string' ? metadata.ports : null, typeof metadata.vmid === 'number' ? `VMID ${metadata.vmid}` : null].filter(Boolean).join(' · ')
  const freshness = metadata.checked_at ?? metadata.observed_at
  return <article className="inventory-row"><span className={`resource-dot ${resource.status}`} aria-hidden="true" /><div className="inventory-main"><div className="inventory-title"><strong>{resource.name}</strong><span className={`status-text ${resource.status}`}>{statusLabel(resource.status)}</span></div><span className="muted">{resource.kind} · {runtime}</span><small>{detail || 'No parent or runtime detail recorded'}{freshness ? ` · ${freshnessLabel(freshness)}` : ''}</small></div><div className="inventory-version"><span className="label">Current</span><strong>{version.current ?? '—'}</strong><span className="label">Latest</span><strong className={version.latest ? '' : 'version-missing'}>{version.latest ?? 'Not checked'}</strong>{version.state !== 'unknown' && <VersionBadge state={version.state} />}</div></article>
}

function hierarchyKind(resource: Resource): string {
  const labels: Record<string, string> = { node: 'Proxmox node', lxc: 'LXC', vm: 'VM', docker_host: 'Docker runtime', container: 'App container', application: 'Application', service: 'Service' }
  return labels[resource.kind] ?? resource.kind
}

function HierarchyNode({ resource, resources, depth = 0 }: { resource: Resource; resources: Resource[]; depth?: number }) {
  const [expanded, setExpanded] = useState(true)
  const childKinds = new Set(['node', 'lxc', 'vm', 'docker_host', 'container', 'application', 'service'])
  const children = sortByStatusThenName(resources.filter((item) => item.parent_id === resource.id && childKinds.has(item.kind)))
  const canExpand = children.length > 0
  return <div className={`hierarchy-node depth-${Math.min(depth, 4)}`}>
    <div className="hierarchy-header">
      {canExpand ? <button type="button" className="tree-toggle" aria-expanded={expanded} aria-label={`${expanded ? 'Collapse' : 'Expand'} ${resource.name}`} onClick={() => setExpanded((value) => !value)}>{expanded ? '−' : '+'}</button> : <span className="tree-spacer" />}
      <div className="hierarchy-identity"><span className="hierarchy-kind">{hierarchyKind(resource)}</span><strong>{resource.name}</strong><span className={`status-text ${resource.status}`}>{statusLabel(resource.status)}</span><span className="hierarchy-parent">{resource.kind === 'docker_host' ? 'Apps below' : resource.kind === 'node' ? 'LXC and VM below' : children.length ? `${children.length} child${children.length === 1 ? '' : 'ren'}` : 'No child resources'}</span></div>
    </div>
    {expanded && children.length > 0 && <div className="hierarchy-children">{resource.kind === 'docker_host' && <div className="hierarchy-group-label">Apps in {resource.name}</div>}{children.map((child) => child.kind === 'container' || child.kind === 'application' || child.kind === 'service' ? <InventoryRow key={child.id} resource={child} resources={resources} /> : <HierarchyNode key={child.id} resource={child} resources={resources} depth={depth + 1} />)}</div>}
  </div>
}

function ServersAppsPanel({ resources }: { resources: Resource[] }) {
  const visibleKinds = new Set(['node', 'lxc', 'vm', 'docker_host', 'container', 'application', 'service'])
  const visible = resources.filter((resource) => visibleKinds.has(resource.kind))
  const roots = sortByStatusThenName(visible.filter((resource) => !resource.parent_id || !visible.some((parent) => parent.id === resource.parent_id)))
  const apps = visible.filter((resource) => ['container', 'application', 'service'].includes(resource.kind))
  return <section id="servers-panel" className="servers-apps-panel" aria-labelledby="servers-apps-title"><div className="panel-heading"><div><p className="eyebrow">PROXMOX RESOURCE TREE</p><h2 id="servers-apps-title" className="section-title">Servers & Apps</h2><p className="muted">Follow the ownership chain: Proxmox → LXC/VM → Docker runtime → apps.</p></div><span className="scope">{roots.length} roots · {apps.length} apps</span></div><div className="hierarchy-panel"><div className="hierarchy-legend"><span><i className="tree-dot server" />Infrastructure</span><span><i className="tree-dot app" />Applications</span><span className="muted">Click −/+ to collapse a branch</span></div>{roots.map((root) => <HierarchyNode key={root.id} resource={root} resources={visible} />)}</div></section>
}

function CronTab({ resources, error }: { resources: Resource[]; error: boolean }) {
  return <section id="cron-panel" aria-label="Cron & scheduled jobs"><SchedulerPanel resources={resources} error={error} /></section>
}

function LogsTab({ logs, logsError, resources }: { logs: LogEntry[]; logsError: boolean; resources: Resource[] }) {
  const [query, setQuery] = useState('')
  const [level, setLevel] = useState('all')
  const [source, setSource] = useState('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const sources = Array.from(new Set(logs.map((log) => log.source))).sort()
  const filtered = logs.filter((log) => (level === 'all' || log.level === level) && (source === 'all' || log.source === source) && `${log.message} ${log.source} ${log.resource_id}`.toLowerCase().includes(query.toLowerCase()))
  const selected = selectedId ? logs.find((log) => log.id === selectedId) : null
  const clearFilters = () => { setQuery(''); setLevel('all'); setSource('all') }
  const copyLog = async (log: LogEntry) => { await navigator.clipboard?.writeText(JSON.stringify(log, null, 2)) }
  const exportLogs = (format: 'json' | 'csv') => {
    const body = format === 'json' ? JSON.stringify(filtered, null, 2) : ['id,observed_at,level,source,resource_id,message', ...filtered.map((log) => [log.id, log.observed_at, log.level, log.source, log.resource_id ?? '', log.message].map((value) => `"${String(value).replace(/"/g, '""')}"`).join(','))].join('\n')
    const blob = new Blob([body], { type: format === 'json' ? 'application/json' : 'text/csv' })
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `homelab-logs.${format}`; anchor.click(); URL.revokeObjectURL(url)
  }
  return <section id="logs-panel" aria-labelledby="logs-tab-title"><div className="panel-heading"><div><p className="eyebrow">EVIDENCE STREAM</p><h2 id="logs-tab-title" className="section-title">Logs</h2><p className="muted">Normalized historical logs with resource context. Live follow remains available through controlled access.</p></div><span className="label">{filtered.length} shown</span></div><div className="logs-toolbar"><label><span className="sr-only">Search logs</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search message, source, resource…" /></label><label><span className="sr-only">Filter log level</span><select value={level} onChange={(event) => setLevel(event.target.value)}><option value="all">All levels</option><option value="critical">Critical</option><option value="error">Error</option><option value="warning">Warning</option><option value="info">Info</option><option value="debug">Debug</option></select></label><label><span className="sr-only">Filter log source</span><select value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All sources</option>{sources.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><button type="button" className="clear-filter-button" onClick={clearFilters}>Clear filters</button><button type="button" className="export-button" onClick={() => exportLogs('json')}>Export JSON</button><button type="button" className="export-button" onClick={() => exportLogs('csv')}>Export CSV</button></div>{logsError ? <p className="state-panel error-state" role="alert">Logs are temporarily unavailable.</p> : <div className="global-log-list">{filtered.map((log) => { const resource = resources.find((item) => item.id === log.resource_id); const parent = resource?.parent_id ? resources.find((item) => item.id === resource.parent_id) : null; return <button className={`global-log-row ${selectedId === log.id ? 'selected' : ''}`} key={log.id} type="button" onClick={() => setSelectedId(log.id)}><div><b className={`log-level ${log.level}`}>{log.level}</b><strong><Highlight text={resource?.name ?? log.resource_id ?? 'Unattributed resource'} query={query} /></strong><span>{[parent?.name, log.source, freshnessLabel(log.observed_at)].filter(Boolean).join(' · ')}</span></div><time dateTime={log.observed_at}>{new Date(log.observed_at).toLocaleString()}</time><p><Highlight text={log.message} query={query} /></p></button> })}{!filtered.length && <p className="empty-state">No log lines match the current filters.</p>}</div>}{selected && <article className="log-detail" aria-live="polite"><div><p className="eyebrow">SELECTED LOG</p><h3>{selected.resource_id ?? 'Unattributed resource'}</h3><code>{selected.id}</code></div><p>{selected.message}</p><dl><div><dt>Level</dt><dd>{selected.level}</dd></div><div><dt>Source</dt><dd>{selected.source}</dd></div><div><dt>Observed</dt><dd>{new Date(selected.observed_at).toLocaleString()}</dd></div></dl><button type="button" className="export-button" onClick={() => void copyLog(selected)}>Copy JSON</button></article>}</section>
}

function safeMetadataText(value: unknown, fallback = 'Unknown'): string {
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return fallback
}

function DeliveryState({ value, label }: { value: unknown; label: string }) {
  const state = safeMetadataText(value, 'unknown')
  const display: Record<string, string> = { generated: 'Generated', success: 'Success', failed: 'Failed', unverified: 'Unverified', attempt_recorded: 'Attempt recorded', not_observed: 'Not observed', unknown: 'Unknown' }
  return <span className={`delivery-state ${state}`}><i aria-hidden="true" />{label}: {display[state] ?? state}</span>
}

function OutputsTab({ outputs, error }: { outputs: AutomationOutput[]; error: boolean }) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const filtered = outputs.filter((output) => {
    const metadata = output.metadata
    const haystack = `${output.name} ${output.id} ${metadata.source_cron_name ?? ''} ${metadata.profile ?? ''} ${metadata.category ?? ''}`.toLowerCase()
    return haystack.includes(query.toLowerCase()) && (category === 'all' || metadata.category === category)
  })
  const categories = Array.from(new Set(outputs.map((output) => safeMetadataText(output.metadata.category, 'other')))).sort()
  return <section id="outputs-panel" aria-labelledby="outputs-title"><div className="panel-heading"><div><p className="eyebrow">AUTOMATION EVIDENCE</p><h2 id="outputs-title" className="section-title">Artifacts & Delivery</h2><p className="muted">Report generation, GitHub synchronization, and Discord delivery are shown as separate evidence states.</p></div><span className="label">{filtered.length} artifacts</span></div><div className="logs-toolbar"><label><span className="sr-only">Search automation outputs</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search artifact, cron, profile…" /></label><label><span className="sr-only">Filter artifact category</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All categories</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><button type="button" className="clear-filter-button" onClick={() => { setQuery(''); setCategory('all') }}>Clear filters</button></div>{error ? <p className="state-panel error-state" role="alert">Automation output evidence is temporarily unavailable.</p> : filtered.length ? <div className="output-list">{filtered.map((output) => { const metadata = output.metadata; const github = (metadata.github ?? {}) as Record<string, unknown>; const discord = (metadata.discord ?? {}) as Record<string, unknown>; const reason = safeMetadataText(github.reason || discord.reason, ''); return <article className="output-card" key={output.id}><div className="output-card-head"><div><p className="eyebrow">{safeMetadataText(metadata.category, 'other')}</p><h3>{output.name}</h3><p className="muted">{safeMetadataText(metadata.source_cron_name)} · profile {safeMetadataText(metadata.profile)}</p></div><span className={`status-text ${output.status}`}>{statusLabel(output.status)}</span></div><dl className="output-facts"><div><dt>Generated</dt><dd>{safeMetadataText(metadata.generated_at, 'Not observed')}</dd></div><div><dt>Artifact</dt><dd>{safeMetadataText(metadata.artifact_type)} · {safeMetadataText(metadata.artifact_size, 'size unknown')}</dd></div><div><dt>Freshness</dt><dd>{freshnessLabel(safeMetadataText(metadata.generated_at, ''))}</dd></div><div><dt>Provenance</dt><dd>{safeMetadataText(metadata.provenance)}</dd></div></dl><div className="delivery-row"><DeliveryState label="Report" value={metadata.artifact_status} /><DeliveryState label="GitHub" value={github.status} /><DeliveryState label="Discord" value={discord.status} /></div><div className="output-targets"><span>GitHub: {safeMetadataText(github.repository_label, 'Not observed')} · {safeMetadataText(github.ref_label, 'ref unknown')}</span><span>Discord: {safeMetadataText(discord.target_label, 'Not observed')}</span></div>{reason && <p className="output-reason">{reason}</p>}{safeMetadataText(metadata.report_preview, '') && <details className="report-preview"><summary>View safe report</summary><pre>{safeMetadataText(metadata.report_preview)}</pre></details>}</article> })}</div> : <p className="muted state-panel">No automation artifacts match the current filters.</p>}</section>
}

function OverviewSummary({ data, incidents, resources }: { data: OverviewData; incidents: Incident[]; resources: Resource[] }) {
  const up = data.status_counts.up ?? 0
  const degraded = data.status_counts.degraded ?? 0
  const down = data.status_counts.down ?? 0
  const unknown = data.status_counts.unknown ?? 0
  const infrastructure = resources.filter((resource) => ['node', 'lxc', 'vm'].includes(resource.kind)).length
  const applications = resources.filter((resource) => ['container', 'application', 'service'].includes(resource.kind)).length
  return <section className="overview-summary" aria-label="Homelab summary"><p>Homelab ini memantau <strong>{data.resource_count} resource</strong> dari {Object.keys(data.source_counts).length} sumber, dengan {infrastructure} resource infrastruktur dan {applications} aplikasi/service yang teridentifikasi. Hierarchy utama dapat ditelusuri dari Proxmox ke LXC/VM, runtime, lalu aplikasi.</p><p>Saat ini <strong>{up} resource up</strong>, {degraded} degraded, {down} down, dan {unknown} unknown. {incidents.length ? `Ada ${incidents.length} incident terbuka yang perlu diperhatikan.` : 'Tidak ada incident terbuka yang tercatat.'} Data ini adalah hasil observasi collector terakhir, bukan tindakan perubahan terhadap workload.</p></section>
}

function OverviewContent({ data, events, incidents, incidentsError, resources, resourcesError, outputs, outputsError, selectedId, onSelect, logs, logsLoading, logsError, activeTab }: { data: OverviewData; events: StatusEvent[]; incidents: Incident[]; incidentsError: boolean; resources: Resource[]; resourcesError: boolean; outputs: AutomationOutput[]; outputsError: boolean; selectedId: string | null; onSelect: (id: string) => void; logs: LogEntry[]; logsLoading: boolean; logsError: boolean; activeTab: TabKey }) {
  if (activeTab === 'servers') return <><ServersAppsPanel resources={resources} /><AccessConsole resources={resources} /></>
  if (activeTab === 'cron') return <CronTab resources={resources} error={resourcesError} />
  if (activeTab === 'logs') return <LogsTab logs={logs} logsError={logsError} resources={resources} />
  if (activeTab === 'outputs') return <OutputsTab outputs={outputs} error={outputsError} />

  const latest = data.latest_collector_run
  const healthy = data.status_counts.up ?? 0
  const degraded = data.status_counts.degraded ?? 0
  return (
    <>
      <section className="hero-grid" aria-label="Monitoring summary">
        <article className="hero-card hero-card-primary"><div><p className="eyebrow">OBSERVED INVENTORY</p><h2>{data.resource_count}</h2><p className="muted">Resources tracked across the homelab</p></div><div className="hero-foot"><span className="signal up" />{healthy} healthy <span className="divider" /> {degraded} degraded</div></article>
        <article className="metric-card"><span className="label">Latest collector</span><strong className="metric-value">{latest?.status ?? 'No run'}</strong><span className="muted">{latest ? `${latest.resource_count} resources · ${latest.error_count} errors` : 'Waiting for first run'}</span></article>
        <article className="metric-card"><span className="label">Sources</span><strong className="metric-value">{Object.keys(data.source_counts).length}</strong><span className="muted">Proxmox and Docker observed</span></article>
      </section>
      <OverviewSummary data={data} incidents={incidents} resources={resources} />
      <section className="content-grid">
        <article className="panel"><div className="panel-heading"><div><p className="eyebrow">STATUS</p><h3>Current health</h3></div><span className="live-pill"><i />Live data</span></div><StatusList data={data} /></article>
        <article className="panel"><div className="panel-heading"><div><p className="eyebrow">SCOPE</p><h3>By source</h3></div></div><div className="source-list">{Object.entries(data.source_counts).map(([source, count]) => <div className="source-row" key={source}><span>{source}</span><strong>{count}</strong></div>)}</div></article>
      </section>
      <TransitionTimeline events={events} />
      <IncidentPanel incidents={incidents} error={incidentsError} />
    </>
  )
}

export default function App() {
  const [data, setData] = useState<OverviewData | null>(null)
  const [resources, setResources] = useState<Resource[]>([])
  const [outputs, setOutputs] = useState<AutomationOutput[]>([])
  const [outputsError, setOutputsError] = useState(false)
  const [resourcesError, setResourcesError] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsError, setLogsError] = useState(false)
  const [events, setEvents] = useState<StatusEvent[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [incidentsError, setIncidentsError] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('overview')

  const loadDashboard = async () => {
    setRefreshing(true)
    const [overviewResult, resourcesResult, outputsResult, versionsResult, eventsResult, incidentsResult] = await Promise.allSettled([fetchOverview(), fetchResources(), fetchAutomationOutputs(), fetchVersions(), fetchStatusEvents(), fetchIncidents()])
    if (overviewResult.status === 'fulfilled') {
      setData(overviewResult.value.data)
      setError(null)
      setLastUpdated(new Date())
    } else {
      setError('Overview is temporarily unavailable.')
    }
    if (resourcesResult.status === 'fulfilled') {
      const versionData = versionsResult.status === 'fulfilled' ? versionsResult.value.data : {}
      const enrichedResources = resourcesResult.value.data.map((resource) => {
        const version = versionData[resource.id]
        if (!version) return resource
        return { ...resource, metadata: { ...resource.metadata, current_version: version.current_version, latest_version: version.latest_version, version_source: version.version_source, update_status: version.update_status } }
      })
      setResources(enrichedResources)
      setSelectedId((current) => current ?? enrichedResources[0]?.id ?? null)
      setResourcesError(false)
    } else {
      setResourcesError(true)
    }
    if (outputsResult.status === 'fulfilled') {
      setOutputs(outputsResult.value.data)
      setOutputsError(false)
    } else {
      setOutputsError(true)
    }
    if (eventsResult.status === 'fulfilled') setEvents(eventsResult.value.data)
    if (incidentsResult.status === 'fulfilled') {
      setIncidents(incidentsResult.value.data)
      setIncidentsError(false)
    } else {
      setIncidentsError(true)
    }
    setRefreshing(false)
  }

  useEffect(() => {
    let cancelled = false
    if (activeTab !== 'logs' && !selectedId) {
      setLogs([])
      return
    }
    setLogsLoading(true)
    void fetchLogs(activeTab === 'logs' ? null : selectedId, activeTab === 'logs' ? 200 : 50).then((result) => {
      if (!cancelled) {
        setLogs(result.data)
        setLogsError(false)
      }
    }).catch(() => {
      if (!cancelled) setLogsError(true)
    }).finally(() => {
      if (!cancelled) setLogsLoading(false)
    })
    return () => { cancelled = true }
  }, [activeTab, selectedId])

  useEffect(() => {
    void loadDashboard()
    const timer = window.setInterval(() => void loadDashboard(), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  return (
    <main className="shell">
      <header className="topbar"><div><p className="eyebrow">HOMELAB CONTROL CENTER</p><h1>{activeTab === 'overview' ? 'Monitoring overview' : activeTab === 'servers' ? 'Servers & Apps' : activeTab === 'outputs' ? 'Artifacts & Delivery' : 'Logs'}</h1><p className="subtitle">A quiet, evidence-backed view of your local infrastructure.</p></div><div className="header-actions"><span className="scope">Local only <span>·</span> Read-only</span><button className="refresh-button" type="button" onClick={() => void loadDashboard()} disabled={refreshing} aria-label="Refresh monitoring overview">{refreshing ? 'Refreshing…' : 'Refresh'}</button></div></header>
      <CollectorPulse events={events} latestStatus={data?.latest_collector_run?.status} />
      <TabNav active={activeTab} onChange={setActiveTab} />
      {error ? <section className="state-panel error-state" role="alert"><strong>Unable to load overview</strong><p>{error}</p></section> : data ? <OverviewContent data={data} events={events} incidents={incidents} incidentsError={incidentsError} resources={resources} resourcesError={resourcesError} outputs={outputs} outputsError={outputsError} selectedId={selectedId} onSelect={setSelectedId} logs={logs} logsLoading={logsLoading} logsError={logsError} activeTab={activeTab} /> : <section className="state-panel" aria-live="polite"><span className="loader" />Loading observed inventory…</section>}
      <footer className="footer"><span>HOMELAB MONITOR</span><span>{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Waiting for data'} · Read-only observability</span></footer>
    </main>
  )
}
