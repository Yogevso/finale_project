import { afterEach, describe, expect, it, vi } from 'vitest'

import { publicApi } from '@/lib/publicApi'

describe('publicApi freshness', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('bypasses browser cache for public document listings', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 1,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )

    await publicApi.getDocuments()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/public/documents?',
      expect.objectContaining({ cache: 'no-store' }),
    )
  })

  it('bypasses browser cache for platform overview reads', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await publicApi.getPlatformsOverview()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/platforms',
      expect.objectContaining({ cache: 'no-store' }),
    )
  })
})
