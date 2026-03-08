import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
        setError(loginError.response?.data?.detail || 'Login failed. Please check your credentials.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-md">
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
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
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
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                Password
              </label>
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
