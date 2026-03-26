import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CollaborationApiMixin } from './collaborationApi'
import { API_BASE_URL, ApiHttpClient } from './httpClient'
import { TRACE_ID_HEADER } from '@/lib/requestTrace'

const mockAxiosInstance = {
  post: vi.fn(),
  get: vi.fn(),
  interceptors: {
    request: {
      use: vi.fn(),
    },
    response: {
      use: vi.fn(),
    },
  },
}

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
    post: vi.fn(),
  },
}))

const mockedAxios = vi.mocked(axios, true)
const CollaborationClient = CollaborationApiMixin(ApiHttpClient)

describe('CollaborationApiMixin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses keepalive fetch when ending a collaboration session in the browser', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new CollaborationClient()
    client.setToken('access-token-123')

    await client.endCollaborationSession('session-123', 7)

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/collaboration/sessions/end`,
      expect.objectContaining({
        method: 'POST',
        keepalive: true,
        credentials: 'include',
        body: JSON.stringify({
          session_id: 'session-123',
          edits_count: 7,
        }),
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token-123',
          'Content-Type': 'application/json',
          [TRACE_ID_HEADER]: expect.any(String),
        }),
      }),
    )
    expect(mockAxiosInstance.post).not.toHaveBeenCalled()
  })

  it('falls back to the axios client when fetch is unavailable', async () => {
    vi.stubGlobal('fetch', undefined as unknown as typeof fetch)
    mockAxiosInstance.post.mockResolvedValue({ data: undefined })

    const client = new CollaborationClient()

    await client.endCollaborationSession('session-456', 2)

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/collaboration/sessions/end', {
      session_id: 'session-456',
      edits_count: 2,
    })
    expect(mockedAxios.create).toHaveBeenCalled()
  })
})
