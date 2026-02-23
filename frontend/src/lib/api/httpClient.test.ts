import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_BASE_URL, ApiHttpClient } from './httpClient'

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

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
    post: vi.fn(),
  },
}))

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
    localStorage.setItem('token', 'expired-token')
    localStorage.setItem('refreshToken', 'refresh-token')

    mockedAxios.post.mockResolvedValue({
      data: {
        access_token: 'new-access-token',
      },
    } as never)

    new ApiHttpClient()

    expect(onResponseError).toBeTruthy()

    const requestOne = onResponseError!(create401Error('/documents/1'))
    const requestTwo = onResponseError!(create401Error('/documents/2'))
    await Promise.all([requestOne, requestTwo])

    expect(mockedAxios.post).toHaveBeenCalledTimes(1)
    expect(mockedAxios.post).toHaveBeenCalledWith(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: 'refresh-token',
    })
    expect(localStorage.getItem('token')).toBe('new-access-token')
    expect(mockAxiosInstance).toHaveBeenCalledTimes(2)

    for (const [requestConfig] of mockAxiosInstance.mock.calls) {
      const config = requestConfig as { headers?: Record<string, string> } | undefined
      expect(config?.headers?.Authorization).toBe('Bearer new-access-token')
    }
  })

  it('rejects all queued requests and clears tokens when refresh fails', async () => {
    localStorage.setItem('token', 'expired-token')
    localStorage.setItem('refreshToken', 'refresh-token')

    mockedAxios.post.mockRejectedValue(new Error('refresh failed'))

    new ApiHttpClient()

    expect(onResponseError).toBeTruthy()

    const requestOne = onResponseError!(create401Error('/documents/1'))
    const requestTwo = onResponseError!(create401Error('/documents/2'))

    await expect(requestOne).rejects.toThrow('refresh failed')
    await expect(requestTwo).rejects.toThrow('refresh failed')

    expect(mockedAxios.post).toHaveBeenCalledTimes(1)
    expect(mockAxiosInstance).toHaveBeenCalledTimes(0)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('refreshToken')).toBeNull()
  })
})
