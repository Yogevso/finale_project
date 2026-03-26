import axios, { AxiosError, AxiosInstance } from 'axios'
import type { TokenResponse } from '@/types'
import { withTraceHeader } from '@/lib/requestTrace'

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

type RefreshSubscriber = {
  resolve: (token: string) => void
  reject: (error: unknown) => void
}

type MutableRequestConfig = {
  headers?: unknown
  url?: string
}

export type Constructor<T = object> = new (...args: any[]) => T

export class ApiHttpClient {
  protected client: AxiosInstance
  private token: string | null = null
  private refreshToken: string | null = null
  private isRefreshing = false
  private refreshSubscribers: RefreshSubscriber[] = []
  private hasRedirectedToLogin = false

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      // AD-004: send httpOnly cookies for session persistence
      withCredentials: true,
      timeout: 30_000,
    })

    // AD-004: tokens are stored in memory only — not localStorage.
    // On page reload they are restored from httpOnly session cookie
    // by the auth interceptor / refresh flow.
    this.token = null
    this.refreshToken = null

    // Migrate: remove any leftover localStorage tokens from pre-AD-004 installs
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
    }

    // Add auth header to requests
    this.client.interceptors.request.use((config) => {
      const headers = withTraceHeader((config.headers ?? {}) as Record<string, string>)
      config.headers = headers
      if (this.token) {
        headers.Authorization = `Bearer ${this.token}`
      }
      return config
    })

    // Handle 401 errors with token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config
        const requestUrl = originalRequest?.url || ''
        const isAuthFlowRequest =
          requestUrl.includes('/auth/login') ||
          requestUrl.includes('/auth/forgot-password') ||
          requestUrl.includes('/auth/refresh')

        if (error.response?.status === 401 && originalRequest && !isAuthFlowRequest) {
          // Try to refresh the token (in-memory refresh token OR httpOnly cookie)
          if (!this.isRefreshing) {
            this.isRefreshing = true
            try {
              const newToken = await this.doRefreshToken()
              this.isRefreshing = false
              this.onRefreshed(newToken)
              this.setAuthHeader(originalRequest, newToken)
              return this.client(originalRequest)
            } catch (refreshError) {
              this.isRefreshing = false
              this.onRefreshFailed(refreshError)
              this.forceLogoutAndRedirect()
              return Promise.reject(refreshError)
            }
          } else if (this.isRefreshing) {
            // Wait for token refresh
            return new Promise((resolve, reject) => {
              this.subscribeTokenRefresh(
                (token: string) => {
                  this.setAuthHeader(originalRequest, token)
                  resolve(this.client(originalRequest))
                },
                (refreshError: unknown) => {
                  reject(refreshError)
                },
              )
            })
          } else {
            this.forceLogoutAndRedirect()
            return Promise.reject(error)
          }
        }
        return Promise.reject(error)
      },
    )
  }

  /** Expose current in-memory access token (read-only). */
  getToken(): string | null {
    return this.token
  }

  protected resolveAttachmentAccessToken(): string | null {
    // AD-004: tokens live in memory only — no localStorage fallback
    if (this.token && this.token !== 'null' && this.token !== 'undefined') {
      return this.token
    }
    return null
  }

  private setAuthHeader(request: MutableRequestConfig, token: string) {
    const headers = withTraceHeader(
      request.headers && typeof request.headers === 'object'
        ? (request.headers as Record<string, string>)
        : {},
    )
    request.headers = headers
    headers.Authorization = `Bearer ${token}`
  }

  private subscribeTokenRefresh(
    resolve: (token: string) => void,
    reject: (error: unknown) => void,
  ) {
    this.refreshSubscribers.push({ resolve, reject })
  }

  private onRefreshed(token: string) {
    this.refreshSubscribers.forEach(({ resolve }) => resolve(token))
    this.refreshSubscribers = []
  }

  private onRefreshFailed(error: unknown) {
    this.refreshSubscribers.forEach(({ reject }) => reject(error))
    this.refreshSubscribers = []
  }

  private forceLogoutAndRedirect() {
    this.clearTokens()
    if (typeof window === 'undefined' || this.hasRedirectedToLogin) {
      return
    }
    this.hasRedirectedToLogin = true
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }

  private async doRefreshToken(): Promise<string> {
    const { data } = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: this.refreshToken },
      // AD-004: send httpOnly cookie for refresh when in-memory token absent
      { withCredentials: true },
    )
    this.setToken(data.access_token, data.refresh_token ?? undefined)
    return data.access_token
  }

  /**
   * AD-004: Attempt to restore session from httpOnly refresh cookie.
   * Call once on app init — if a valid refresh cookie exists the backend
   * returns a fresh access token.
   */
  async tryRestoreSession(): Promise<boolean> {
    try {
      const { data } = await axios.post<TokenResponse>(
        `${API_BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true },
      )
      if (data.access_token) {
        this.setToken(data.access_token, data.refresh_token ?? undefined)
        return true
      }
    } catch {
      // no valid cookie — user needs to log in
    }
    return false
  }

  setToken(token: string, refresh?: string | null) {
    this.token = token
    this.hasRedirectedToLogin = false
    // AD-004: tokens stored in memory only — not localStorage
    if (refresh !== undefined) {
      this.refreshToken = refresh ?? null
    }
  }

  clearTokens() {
    this.token = null
    this.refreshToken = null
    // AD-004: clean up any stale localStorage keys from pre-migration
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
    }
  }

  hasToken(): boolean {
    return !!this.token
  }
}
