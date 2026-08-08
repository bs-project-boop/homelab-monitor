import { describe, expect, it } from 'vitest'

import { inventorySection, sortByStatusThenName, versionInfo } from './inventory'
import type { Resource } from './api'

const resource = (overrides: Partial<Resource>): Resource => ({ id: 'x', kind: 'container', name: 'app', source: 'docker', status: 'up', parent_id: null, metadata: {}, ...overrides })

describe('inventory view model', () => {
  it('classifies servers, apps, and schedulers separately', () => {
    expect(inventorySection(resource({ kind: 'lxc' }))).toBe('server')
    expect(inventorySection(resource({ kind: 'container' }))).toBe('app')
    expect(inventorySection(resource({ kind: 'cron_job' }))).toBe('cron')
  })

  it('derives current Docker version from image without inventing latest', () => {
    expect(versionInfo(resource({ metadata: { image: 'jellyfin/jellyfin:10.11.11' } }))).toEqual({ current: '10.11.11', latest: null, source: null, state: 'unknown' })
  })

  it('marks an explicit trusted latest version as update available', () => {
    expect(versionInfo(resource({ metadata: { current_version: '1.2.0', latest_version: '1.3.0', version_source: 'docker-hub' } })).state).toBe('update_available')
  })

  it('respects backend unknown state for mutable latest tags', () => {
    expect(versionInfo(resource({ metadata: { current_version: 'latest', latest_version: '2.7.3', version_source: 'docker-hub', update_status: 'unknown' } })).state).toBe('unknown')
  })

  it('sorts down and degraded resources before healthy resources', () => {
    const sorted = sortByStatusThenName([resource({ id: 'a', name: 'healthy' }), resource({ id: 'b', name: 'down', status: 'down' }), resource({ id: 'c', name: 'degraded', status: 'degraded' })])
    expect(sorted.map((item) => item.name)).toEqual(['down', 'degraded', 'healthy'])
  })
})
