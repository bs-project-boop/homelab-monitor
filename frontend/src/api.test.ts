import { describe, expect, it, vi } from 'vitest'

import { createAccessSession, fetchLogs, fetchOverview, fetchResources, fetchStatusEvents } from './api'

describe('overview API client', () => {
  it('requests the versioned overview endpoint and returns its envelope', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { resource_count: 29 }, freshness: 'fresh' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await fetchOverview(fetcher)

    expect(fetcher).toHaveBeenCalledWith('/api/v1/overview', {
      headers: { Accept: 'application/json' },
    })
    expect(result.data.resource_count).toBe(29)
  })

  it('requests the bounded resource inventory endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: [{ id: 'proxmox:vm:111', kind: 'vm' }], freshness: 'fresh' }), { status: 200 }),
    )

    const result = await fetchResources(fetcher)

    expect(fetcher).toHaveBeenCalledWith('/api/v1/resources', {
      headers: { Accept: 'application/json' },
    })
    expect(result.data[0].id).toBe('proxmox:vm:111')
  })

  it('requests logs for a selected resource with a bounded limit', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: [], freshness: 'empty' }), { status: 200 }))

    await fetchLogs('proxmox:vm:111', 500, fetcher)

    expect(fetcher).toHaveBeenCalledWith('/api/v1/logs?limit=200&resource_id=proxmox%3Avm%3A111', {
      headers: { Accept: 'application/json' },
    })
  })

  it('requests the bounded status history endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: [], freshness: 'empty' }), { status: 200 }),
    )

    await fetchStatusEvents(8, fetcher)

    expect(fetcher).toHaveBeenCalledWith('/api/v1/status-events?limit=8', {
      headers: { Accept: 'application/json' },
    })
  })

  it('opens an authenticated allowlisted access session', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ session_id: 's1', target: 'pve', mode: 'logs', expires_at: 123 }), { status: 201 }))
    const result = await createAccessSession('pve', 'logs', 'operator-token', fetcher)
    expect(result.session_id).toBe('s1')
    expect(fetcher).toHaveBeenCalledWith('/api/v1/access/sessions', expect.objectContaining({ method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer operator-token' }) }))
  })

  it('turns non-success responses into a user-safe error', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('', { status: 503 }))

    await expect(fetchOverview(fetcher)).rejects.toThrow('Unable to load monitoring overview')
  })
})
