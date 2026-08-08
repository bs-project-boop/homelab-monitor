import { describe, expect, it, vi } from 'vitest'

import { fetchIncidents } from './api'

describe('incidents API client', () => {
  it('requests bounded open incidents and preserves the envelope', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        data: [{ id: 'incident:test', status: 'open', severity: 'warning' }],
        freshness: 'fresh',
      }), { status: 200 }),
    )

    const result = await fetchIncidents(6, fetcher)

    expect(fetcher).toHaveBeenCalledWith('/api/v1/incidents?status=open&limit=6', {
      headers: { Accept: 'application/json' },
    })
    expect(result.data[0].severity).toBe('warning')
  })

  it('returns a safe error for unavailable incident data', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('', { status: 503 }))
    await expect(fetchIncidents(6, fetcher)).rejects.toThrow('Unable to load incidents')
  })
})
