import type { MonitorStatus, Resource } from './api'

export type InventorySection = 'server' | 'app' | 'cron' | 'other'
export type UpdateState = 'up_to_date' | 'update_available' | 'unknown'

export interface VersionInfo {
  current: string | null
  latest: string | null
  source: string | null
  state: UpdateState
}

export function inventorySection(resource: Resource): InventorySection {
  if (['node', 'vm', 'lxc', 'docker_host', 'host'].includes(resource.kind)) return 'server'
  if (['container', 'application', 'service', 'dependency'].includes(resource.kind)) return 'app'
  if (['cron_profile', 'cron_job'].includes(resource.kind)) return 'cron'
  return 'other'
}

export function statusLabel(status: MonitorStatus): string {
  return status === 'up' ? 'Up' : status === 'degraded' ? 'Degraded' : status === 'down' ? 'Down' : status === 'maintenance' ? 'Maintenance' : 'Unknown'
}

function stringValue(metadata: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = metadata[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
    if (typeof value === 'number') return String(value)
  }
  return null
}

function imageTag(image: string | null): string | null {
  if (!image) return null
  const last = image.split('/').at(-1) ?? image
  const separator = last.lastIndexOf(':')
  return separator > -1 ? last.slice(separator + 1) : null
}

export function versionInfo(resource: Resource): VersionInfo {
  const metadata = resource.metadata
  const image = stringValue(metadata, ['image'])
  const current = stringValue(metadata, ['current_version', 'version', 'docker_version', 'pveversion']) ?? imageTag(image)
  const latest = stringValue(metadata, ['latest_version', 'available_version'])
  const source = stringValue(metadata, ['version_source', 'latest_source'])
  const declaredState = stringValue(metadata, ['update_status'])
  let state: UpdateState = declaredState === 'up_to_date' || declaredState === 'update_available' || declaredState === 'unknown' ? declaredState : 'unknown'
  if (!declaredState && current && latest) state = current === latest ? 'up_to_date' : 'update_available'
  return { current, latest, source, state }
}

export function sortByStatusThenName(resources: Resource[]): Resource[] {
  const order: Record<MonitorStatus, number> = { down: 0, degraded: 1, unknown: 2, maintenance: 3, up: 4 }
  return [...resources].sort((left, right) => (order[left.status] - order[right.status]) || left.name.localeCompare(right.name))
}
