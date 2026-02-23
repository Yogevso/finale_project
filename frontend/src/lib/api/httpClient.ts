import axios, { AxiosError, AxiosInstance } from 'axios'
import type { TokenResponse } from '@/types'

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
    })

    // Load tokens from localStorage
    this.token = localStorage.getItem('token')
    this.refreshToken = localStorage.getItem('refreshToken')

    // Add auth header to requests
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`
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
          // Try to refresh the token
          if (this.refreshToken && !this.isRefreshing) {
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

  protected resolveAttachmentAccessToken(): string | null {
    const authToken = this.token || localStorage.getItem('token')
    if (authToken && authToken !== 'null' && authToken !== 'undefined') {
      return authToken
    }
    if (typeof window !== 'undefined') {
      const urlToken = new URLSearchParams(window.location.search).get('token')
      if (urlToken && urlToken !== 'null' && urlToken !== 'undefined') {
        return urlToken
      }
    }
    return null
  }

  private setAuthHeader(request: MutableRequestConfig, token: string) {
    if (!request.headers || typeof request.headers !== 'object') {
      request.headers = {}
    }
    const headers = request.headers as Record<string, string>
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
    )
    this.setToken(data.access_token)
    return data.access_token
  }

  setToken(token: string, refresh?: string | null) {
    this.token = token
    this.hasRedirectedToLogin = false
    localStorage.setItem('token', token)
    if (refresh !== undefined) {
      this.refreshToken = refresh
      if (refresh) {
        localStorage.setItem('refreshToken', refresh)
      } else {
        localStorage.removeItem('refreshToken')
      }
    }
  }

  clearTokens() {
    this.token = null
    this.refreshToken = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  hasToken(): boolean {
    return !!this.token
  }
}
