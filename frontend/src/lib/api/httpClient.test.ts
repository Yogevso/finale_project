import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_BASE_URL, ApiHttpClient } from './httpClient'
import { TRACE_ID_HEADER } from '@/lib/requestTrace'

type MockResponseErrorHandler = (error: {
  config?: { url?: string; headers?: Record<string, string> }
  response?: { status?: number }
}) => Promise<unknown>

let onResponseError: MockResponseErrorHandler | null = null

const mockAxiosInstance = Object.assign(
  vi.fn(async (config?: { headers?: Record<string, string> }) => ({ data: config })),
  {
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn((_: unknown, onRejected: MockResponseErrorHandler) => {
          onResponseError = onRejected
        }),
      },
    },
  },
)

vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal<typeof import('axios')>()
  const mockedDefault = {
    ...actual.default,
    create: vi.fn(() => mockAxiosInstance),
    post: vi.fn(),
  }

  return {
    ...actual,
    default: mockedDefault,
  }
})

const mockedAxios = vi.mocked(axios, true)

function create401Error(url: string) {
  return {
    config: { url, headers: {} },
    response: { status: 401 },
  }
}

describe('ApiHttpClient refresh interceptor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    onResponseError = null
    localStorage.clear()
    window.history.pushState({}, '', '/login')
  })

  it('retries queued 401 requests after a successful refresh', async () => {
    mockedAxios.post.mockResolvedValue({
      data: {
        access_token: 'new-access-token',
      },
    } as never)

    const client = new ApiHttpClient()
    // AD-004: tokens are set in memory via setToken, not localStorage
    client.setToken('expired-token', 'refresh-token')

    expect(onResponseError).toBeTruthy()

    const requestOne = onResponseError!(create401Error('/documents/1'))
    const requestTwo = onResponseError!(create401Error('/documents/2'))
    await Promise.all([requestOne, requestTwo])

    expect(mockedAxios.post).toHaveBeenCalledTimes(1)
    expect(mockedAxios.post).toHaveBeenCalledWith(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: 'refresh-token' },
      { withCredentials: true },
    )
    expect(client.getToken()).toBe('new-access-token')
    expect(mockAxiosInstance).toHaveBeenCalledTimes(2)

    for (const [requestConfig] of mockAxiosInstance.mock.calls) {
      const config = requestConfig as { headers?: Record<string, string> } | undefined
      expect(config?.headers?.Authorization).toBe('Bearer new-access-token')
      expect(config?.headers?.[TRACE_ID_HEADER]).toBeTruthy()
    }
  })

  it('rejects all queued requests and clears tokens when refresh fails', async () => {
    mockedAxios.post.mockRejectedValue(new Error('refresh failed'))

    const client = new ApiHttpClient()
    client.setToken('expired-token', 'refresh-token')

    expect(onResponseError).toBeTruthy()

    const requestOne = onResponseError!(create401Error('/documents/1'))
    const requestTwo = onResponseError!(create401Error('/documents/2'))

    await expect(requestOne).rejects.toThrow('refresh failed')
    await expect(requestTwo).rejects.toThrow('refresh failed')

    expect(mockedAxios.post).toHaveBeenCalledTimes(1)
    expect(mockAxiosInstance).toHaveBeenCalledTimes(0)
    expect(client.getToken()).toBeNull()
  })

  it('adds a trace header to outgoing requests and preserves an existing one', () => {
    const client = new ApiHttpClient()
    client.setToken('access-token')

    const onRequest = mockAxiosInstance.interceptors.request.use.mock.calls[0]?.[0] as
      | ((config: { headers?: Record<string, string> }) => { headers?: Record<string, string> })
      | undefined

    expect(onRequest).toBeTruthy()

    const traced = onRequest!({ headers: {} })
    expect(traced.headers?.Authorization).toBe('Bearer access-token')
    expect(traced.headers?.[TRACE_ID_HEADER]).toBeTruthy()

    const existing = onRequest!({ headers: { [TRACE_ID_HEADER]: 'trace-existing' } })
    expect(existing.headers?.[TRACE_ID_HEADER]).toBe('trace-existing')
  })
})
