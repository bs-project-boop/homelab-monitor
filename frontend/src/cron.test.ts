import { describe, expect, it } from 'vitest'

import type { Resource } from './api'
import { classifyScheduler, explainCron } from './cron'

const resource = (overrides: Partial<Resource>): Resource => ({ id: 'job-1', name: 'homelab-daily-infra-map-only', kind: 'cron_job', status: 'up', source: 'hermes', parent_id: 'profile-cron', metadata: { schedule: '0 0 * * *', skills: 'homelab-management, docker-management', deliver: 'discord:123', state: 'active' }, ...overrides })

describe('cron explanations', () => {
  it('explains Hermes profile ownership and purpose in plain language', () => {
    const job = resource({ name: 'homelab-daily-infra-map-only' })
    const result = explainCron(job, [{ id: 'profile-cron', name: 'sysadmin cron', kind: 'cron_profile', status: 'up', source: 'hermes', parent_id: 'profile-owner', metadata: { job_count: 1 } }, { id: 'profile-owner', name: 'sysadmin', kind: 'hermes_profile', status: 'up', source: 'hermes', parent_id: null, metadata: {} }])
    expect(result.owner).toBe('Hermes profile sysadmin')
    expect(result.purpose).toContain('pemetaan dan pemeriksaan infrastruktur homelab')
    expect(result.executor).toContain('Hermes profile')
    expect(result.schedule).toBe('Setiap hari tengah malam')
  })

  it('classifies OS cron with an LXC parent as system, not Hermes', () => {
    const job = resource({ id: 'system-1', name: '/etc/cron.d/certbot entry 2', source: 'cron', parent_id: 'lxc-cron' })
    const resources: Resource[] = [{ id: 'lxc-cron', name: 'LXC cron', kind: 'cron_profile', status: 'up', source: 'cron', parent_id: 'lxc-106', metadata: {} }, { id: 'lxc-106', name: 'cloudflared', kind: 'lxc', status: 'up', source: 'proxmox', parent_id: null, metadata: {} }]
    expect(classifyScheduler(job, resources)).toBe('system_scheduler')
  })

  it('classifies a Hermes job only with a Hermes profile owner', () => {
    const job = resource({ name: 'profile-owned-job' })
    const resources: Resource[] = [{ id: 'profile-cron', name: 'default cron', kind: 'cron_profile', status: 'up', source: 'hermes', parent_id: 'profile-owner', metadata: {} }, { id: 'profile-owner', name: 'default', kind: 'hermes_profile', status: 'up', source: 'hermes', parent_id: null, metadata: {} }]
    expect(classifyScheduler(job, resources)).toBe('hermes_profile')
  })

  it('uses the captured prompt scope instead of a generic name inference', () => {
    const job = resource({ name: 'audit-daily' })
    const result = explainCron(job, [{ id: 'profile-cron', name: 'default cron', kind: 'cron_profile', status: 'up', source: 'hermes', parent_id: 'profile-owner', metadata: {} }, { id: 'profile-owner', name: 'default', kind: 'hermes_profile', status: 'up', source: 'hermes', parent_id: null, metadata: {} }])
    expect(result.purpose).toContain('audit operasional harian')
    expect(result.why).toContain('Proxmox PVE')
    expect(result.purposeBasis).toContain('prompt/job snapshot')
  })

})

