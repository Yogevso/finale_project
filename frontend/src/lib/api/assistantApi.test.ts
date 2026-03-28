import { beforeEach, describe, expect, it, vi } from 'vitest'

import assistantApi from './assistantApi'
import { API_BASE_URL } from './httpClient'

vi.mock('@/lib/api', () => ({
  api: {
    getToken: vi.fn(() => 'access-token-123'),
  },
}))

describe('assistantApi.sendMessage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('includes document_ids and file_ids in the streaming request body', async () => {
    const reader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('event: done\ndata: {}\n\n'),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
    }

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: {
        getReader: () => reader,
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    const onEvent = vi.fn()

    await assistantApi.sendMessage(17, 'Summarize this', onEvent, undefined, [4, 5], [11, 12])

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/assistant/chat`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          conversation_id: 17,
          message: 'Summarize this',
          document_ids: [4, 5],
          file_ids: [11, 12],
        }),
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token-123',
          'Content-Type': 'application/json',
        }),
      }),
    )
    expect(onEvent).toHaveBeenCalledWith({ event: 'done', data: {} })
  })
})
