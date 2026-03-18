import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { getHomeRouteForRole } from '@/config/routes'

interface LoginErrorResponse {
  detail?: string
  error_code?: string
  retry_after?: number
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [cooldownSeconds, setCooldownSeconds] = useState(0)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [forgotIdentifier, setForgotIdentifier] = useState('')
  const [forgotMessage, setForgotMessage] = useState('')
  const [forgotError, setForgotError] = useState('')
  const [isForgotLoading, setIsForgotLoading] = useState(false)
  const { login, user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  // If already logged in, redirect to appropriate home
  useEffect(() => {
    if (!authLoading && user) {
      navigate(getHomeRouteForRole(user.role), { replace: true })
    }
  }, [user, authLoading, navigate])

  useEffect(() => {
    if (cooldownSeconds <= 0) return
    const timer = window.setInterval(() => {
      setCooldownSeconds((current) => (current > 1 ? current - 1 : 0))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [cooldownSeconds])

  const applyCooldownFromError = (rawError: unknown): boolean => {
    const axiosLikeError = rawError as {
      response?: {
        status?: number
        headers?: Record<string, string | undefined>
        data?: LoginErrorResponse
      }
    }
    const response = axiosLikeError.response
    if (!response || response.status !== 429) {
      return false
    }

    const retryAfterHeader = Number(response.headers?.['retry-after'] || '')
    const retryAfterBody = Number(response.data?.retry_after || '')
    const retryAfterSeconds = Number.isFinite(retryAfterHeader) && retryAfterHeader > 0
      ? Math.ceil(retryAfterHeader)
      : Number.isFinite(retryAfterBody) && retryAfterBody > 0
        ? Math.ceil(retryAfterBody)
        : 30

    setCooldownSeconds(retryAfterSeconds)
    setError('')
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isLoading || cooldownSeconds > 0) {
      return
    }
    setError('')
    setIsLoading(true)

    try {
      await login({ username, password })
      // After login, useEffect will redirect based on role
    } catch (err: unknown) {
      const isRateLimited = applyCooldownFromError(err)
      if (!isRateLimited) {
        const loginError = err as { response?: { data?: LoginErrorResponse } }
        const detail = loginError.response?.data?.detail
        if (detail === 'email_not_verified') {
          setError('Please verify your email before signing in. Check your inbox for a verification link.')
        } else if (detail === 'account_locked') {
          setError('Your account is temporarily locked after multiple failed attempts. Try again later or contact an admin.')
        } else {
          setError(detail || 'Login failed. Please check your credentials.')
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleForgotPasswordSubmit = async () => {
    if (isForgotLoading) {
      return
    }

    const identifier = forgotIdentifier.trim()
    if (!identifier) {
      setForgotError('Email is required')
      return
    }

    setForgotError('')
    setForgotMessage('')
    setIsForgotLoading(true)

    try {
      const response = await api.forgotPassword(identifier)
      setForgotMessage(response.message)
    } catch {
      setForgotError('Unable to request password reset right now. Please try again later.')
    } finally {
      setIsForgotLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:text-slate-900 focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-sky-500">Skip to main content</a>
      <div id="main-content" className="w-full max-w-md">
        <div className="surface-card rounded-2xl p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 mb-4">
              <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-lg">DP</span>
              </div>
            </div>
            <h1 className="text-3xl font-display font-bold text-slate-900">Documentation Platform</h1>
            <p className="text-slate-500 mt-2">Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {cooldownSeconds > 0 && (
              <div role="alert" aria-live="polite" className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
                Too many sign-in attempts. Try again in {cooldownSeconds} seconds.
              </div>
            )}
            {error && (
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-2">
                Username
              </label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-field"
                placeholder="Enter your username"
                required
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setShowForgotPassword((previous) => !previous)
                    setForgotError('')
                    setForgotMessage('')
                  }}
                  className="text-xs text-sky-600 hover:text-sky-700"
                >
                  Forgot password?
                </button>
              </div>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                placeholder="Enter your password"
                required
              />
            </div>

            {showForgotPassword && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
                <p className="text-sm text-slate-700">Enter your email to receive password reset instructions.</p>
                {forgotMessage && (
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
                    {forgotMessage}
                  </div>
                )}
                {forgotError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                    {forgotError}
                  </div>
                )}
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    type="email"
                    value={forgotIdentifier}
                    onChange={(event) => setForgotIdentifier(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        void handleForgotPasswordSubmit()
                      }
                    }}
                    placeholder="you@example.com"
                    className="input-field flex-1"
                  />
                  <button
                    type="button"
                    onClick={() => void handleForgotPasswordSubmit()}
                    className="btn-secondary"
                    disabled={isForgotLoading}
                  >
                    {isForgotLoading ? 'Sending...' : 'Send Reset Link'}
                  </button>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || cooldownSeconds > 0}
              className="btn-primary w-full py-3"
            >
              {isLoading ? 'Signing in...' : cooldownSeconds > 0 ? `Try again in ${cooldownSeconds}s` : 'Sign In'}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-200">
            <p className="text-sm text-slate-500 text-center mb-3">Demo Credentials (click to login)</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                disabled={isLoading || cooldownSeconds > 0}
                onClick={() => { setUsername('sysadmin'); setPassword('sysadmin123'); setTimeout(() => document.querySelector('form')?.requestSubmit(), 100); }}
                className="p-2 surface-muted rounded-xl text-center hover:bg-slate-100 transition-colors cursor-pointer border border-transparent hover:border-slate-300"
              >
                <div className="font-medium text-purple-700">System Admin</div>
                <div className="text-slate-500">sysadmin / sysadmin123</div>
              </button>
              <button
                type="button"
                disabled={isLoading || cooldownSeconds > 0}
                onClick={() => { setUsername('admin'); setPassword('admin123'); setTimeout(() => document.querySelector('form')?.requestSubmit(), 100); }}
                className="p-2 surface-muted rounded-xl text-center hover:bg-slate-100 transition-colors cursor-pointer border border-transparent hover:border-slate-300"
              >
                <div className="font-medium text-rose-600">Admin</div>
                <div className="text-slate-500">admin / admin123</div>
              </button>
              <button
                type="button"
                disabled={isLoading || cooldownSeconds > 0}
                onClick={() => { setUsername('manager'); setPassword('manager123'); setTimeout(() => document.querySelector('form')?.requestSubmit(), 100); }}
                className="p-2 surface-muted rounded-xl text-center hover:bg-slate-100 transition-colors cursor-pointer border border-transparent hover:border-slate-300"
              >
                <div className="font-medium text-sky-600">Manager</div>
                <div className="text-slate-500">manager / manager123</div>
              </button>
              <button
                type="button"
                disabled={isLoading || cooldownSeconds > 0}
                onClick={() => { setUsername('editor'); setPassword('editor123'); setTimeout(() => document.querySelector('form')?.requestSubmit(), 100); }}
                className="p-2 surface-muted rounded-xl text-center hover:bg-slate-100 transition-colors cursor-pointer border border-transparent hover:border-slate-300"
              >
                <div className="font-medium text-emerald-600">Editor</div>
                <div className="text-slate-500">editor / editor123</div>
              </button>
              <button
                type="button"
                disabled={isLoading || cooldownSeconds > 0}
                onClick={() => { setUsername('customer1'); setPassword('customer123'); setTimeout(() => document.querySelector('form')?.requestSubmit(), 100); }}
                className="p-2 surface-muted rounded-xl text-center col-span-2 hover:bg-slate-100 transition-colors cursor-pointer border border-transparent hover:border-slate-300"
              >
                <div className="font-medium text-amber-600">Customer</div>
                <div className="text-slate-500">customer1 / customer123</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
