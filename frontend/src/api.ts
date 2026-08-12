export type MonitorStatus = 'up' | 'degraded' | 'down' | 'unknown' | 'maintenance'

export interface CollectorRun {
  id: string
  status: string
  started_at: string
  completed_at: string | null
  resource_count: number
  error_count: number
  errors: Array<Record<string, string>>
}

export interface OverviewData {
  resource_count: number
  status_counts: Partial<Record<MonitorStatus, number>>
  kind_counts: Record<string, number>
  source_counts: Record<string, number>
  latest_collector_run: CollectorRun | null
}

export interface Resource {
  id: string
  kind: string
  name: string
  source: string
  status: MonitorStatus
  parent_id: string | null
  metadata: Record<string, unknown>
}

export interface AutomationOutput {
  id: string
  kind: 'artifact'
  name: string
  source: string
  status: MonitorStatus
  metadata: Record<string, unknown>
}

export interface AutomationOutputResponse {
  data: AutomationOutput[]
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

export interface ResourceResponse {
  data: Resource[]
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

export interface OverviewResponse {
  data: OverviewData
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

export interface AccessSession {
  session_id: string
  target: string
  mode: 'shell' | 'logs'
  expires_at: number
}

export interface BootstrapStatus {
  configured: boolean
  recovery_available: boolean
}

export interface BootstrapResponse {
  operator_token: string
  recovery_secret: string
}

export interface VersionCheck {
  current_version: string | null
  latest_version: string | null
  version_source: string | null
  update_status: 'up_to_date' | 'update_available' | 'unknown'
}

export interface VersionResponse {
  data: Record<string, VersionCheck>
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

export interface LogEntry {
  id: string
  resource_id: string
  source: string
  level: string
  message: string
  fingerprint: string
  observed_at: string
  metadata: Record<string, unknown>
}

export interface LogResponse {
  data: LogEntry[]
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

export interface StatusEvent {
  id: number
  resource_id: string
  previous_status: MonitorStatus | null
  status: MonitorStatus
  reason: string
  observed_at: string
  metadata: Record<string, unknown>
}

export interface StatusEventResponse {
  data: StatusEvent[]
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

export type IncidentStatus = 'open' | 'resolved'
export type IncidentSeverity = 'info' | 'warning' | 'critical'

export interface Incident {
  id: string
  resource_id: string
  fingerprint: string
  status: IncidentStatus
  severity: IncidentSeverity
  title: string
  opened_at: string
  resolved_at: string | null
  last_seen_at: string
  metadata: Record<string, unknown>
}

export interface IncidentResponse {
  data: Incident[]
  source: string
  persistence: string
  freshness: 'fresh' | 'empty'
  partial_errors: Array<Record<string, string>>
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export async function fetchAutomationOutputs(
  limit = 100,
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<AutomationOutputResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase ? `${configuredBase}/api/v1/automation-outputs?limit=${limit}` : `/api/v1/automation-outputs?limit=${limit}`
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to load automation outputs')
  return (await response.json()) as AutomationOutputResponse
}

export async function fetchResources(
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<ResourceResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase ? `${configuredBase}/api/v1/resources` : '/api/v1/resources'
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to load resource inventory')
  return (await response.json()) as ResourceResponse
}

export async function fetchOverview(
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<OverviewResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase
    ? `${configuredBase}/api/v1/overview`
    : '/api/v1/overview'
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) {
    throw new Error('Unable to load monitoring overview')
  }
  return (await response.json()) as OverviewResponse
}

export async function fetchVersions(
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<VersionResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase ? `${configuredBase}/api/v1/versions` : '/api/v1/versions'
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to load version inventory')
  return (await response.json()) as VersionResponse
}

export async function fetchLogs(
  resourceId: string | null = null,
  limit = 100,
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<LogResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const query = new URLSearchParams({ limit: String(Math.min(Math.max(limit, 1), 200)) })
  if (resourceId) query.set('resource_id', resourceId)
  const endpoint = configuredBase ? `${configuredBase}/api/v1/logs?${query}` : `/api/v1/logs?${query}`
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to load logs')
  return (await response.json()) as LogResponse
}

export async function fetchStatusEvents(
  limit = 8,
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<StatusEventResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase
    ? `${configuredBase}/api/v1/status-events?limit=${limit}`
    : `/api/v1/status-events?limit=${limit}`
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) {
    throw new Error('Unable to load status history')
  }
  return (await response.json()) as StatusEventResponse
}

export async function fetchResourceStatusEvents(
  resourceId: string,
  limit = 20,
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<StatusEventResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const query = new URLSearchParams({ resource_id: resourceId, limit: String(Math.min(Math.max(limit, 1), 200)) })
  const endpoint = configuredBase ? `${configuredBase}/api/v1/status-events?${query}` : `/api/v1/status-events?${query}`
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to load scheduler run history')
  return (await response.json()) as StatusEventResponse
}

export async function fetchBootstrapStatus(fetcher: FetchLike = (...args) => globalThis.fetch(...args)): Promise<BootstrapStatus> {
  const response = await fetcher('/api/v1/access/bootstrap/status', { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to check operator setup')
  return (await response.json()) as BootstrapStatus
}

export async function enrollOperator(fetcher: FetchLike = (...args) => globalThis.fetch(...args)): Promise<BootstrapResponse> {
  const response = await fetcher('/api/v1/access/bootstrap/enroll', { method: 'POST', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(response.status === 409 ? 'Operator access is already configured' : 'Unable to create operator access')
  return (await response.json()) as BootstrapResponse
}

export async function recoverOperator(recoverySecret: string, fetcher: FetchLike = (...args) => globalThis.fetch(...args)): Promise<BootstrapResponse> {
  const response = await fetcher('/api/v1/access/bootstrap/recover', { method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' }, body: JSON.stringify({ recovery_secret: recoverySecret }) })
  if (!response.ok) throw new Error(response.status === 401 ? 'Invalid recovery secret' : 'Unable to recover operator access')
  return (await response.json()) as BootstrapResponse
}

export async function createAccessSession(
  target: string,
  mode: 'shell' | 'logs',
  token: string,
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<AccessSession> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase ? `${configuredBase}/api/v1/access/sessions` : '/api/v1/access/sessions'
  const response = await fetcher(endpoint, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ target, mode }),
  })
  if (!response.ok) throw new Error(response.status === 401 ? 'Invalid operator token' : 'Unable to open access session')
  return (await response.json()) as AccessSession
}

export async function revokeAccessSession(sessionId: string, token: string, fetcher: FetchLike = (...args) => globalThis.fetch(...args)): Promise<void> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const endpoint = configuredBase ? `${configuredBase}/api/v1/access/sessions/${sessionId}` : `/api/v1/access/sessions/${sessionId}`
  await fetcher(endpoint, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
}

export async function fetchIncidents(
  limit = 6,
  fetcher: FetchLike = (...args) => globalThis.fetch(...args),
): Promise<IncidentResponse> {
  const configuredBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  const query = `status=open&limit=${limit}`
  const endpoint = configuredBase
    ? `${configuredBase}/api/v1/incidents?${query}`
    : `/api/v1/incidents?${query}`
  const response = await fetcher(endpoint, { headers: { Accept: 'application/json' } })
  if (!response.ok) {
    throw new Error('Unable to load incidents')
  }
  return (await response.json()) as IncidentResponse
}
