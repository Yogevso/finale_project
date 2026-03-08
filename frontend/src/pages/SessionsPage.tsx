import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Laptop, LogOut, MonitorSmartphone, ShieldAlert, Smartphone, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import PageHeader from '@/components/PageHeader'
import ProfileSettingsNav from '@/components/ProfileSettingsNav'
import Skeleton from '@/components/Skeleton'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useToast } from '@/lib/toast'
import type { UserSession } from '@/types'

const MY_SESSIONS_QUERY_KEY = ['my-sessions'] as const

function inferBrowserLabel(userAgent: string | null | undefined): string {
  if (!userAgent) return 'Unknown browser'
  const normalized = userAgent.toLowerCase()
  if (normalized.includes('edg/')) return 'Microsoft Edge'
  if (normalized.includes('chrome/')) return 'Google Chrome'
  if (normalized.includes('safari/') && !normalized.includes('chrome/')) return 'Safari'
  if (normalized.includes('firefox/')) return 'Firefox'
  if (normalized.includes('opr/') || normalized.includes('opera/')) return 'Opera'
  return 'Browser'
}

function inferDeviceIcon(userAgent: string | null | undefined) {
  if (!userAgent) return Laptop
  const normalized = userAgent.toLowerCase()
  if (normalized.includes('mobile') || normalized.includes('android') || normalized.includes('iphone')) {
    return Smartphone
  }
  return MonitorSmartphone
}

function formatRelativeTime(isoDateTime: string): string {
  const date = new Date(isoDateTime)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 30) return `${diffDays}d ago`
  return date.toLocaleString()
}

export default function SessionsPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const sessionsQuery = useQuery({
    queryKey: MY_SESSIONS_QUERY_KEY,
    queryFn: () => api.getMySessions(),
  })

  const revokeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => api.revokeMySession(sessionId),
    onSuccess: () => {
      toast.success('Session revoked')
      queryClient.invalidateQueries({ queryKey: MY_SESSIONS_QUERY_KEY })
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to revoke session'
      toast.error('Could not revoke session', message)
    },
  })

  const revokeAllSessionsMutation = useMutation({
    mutationFn: () => api.revokeAllMyOtherSessions(),
    onSuccess: async (payload) => {
      toast.success('Signed out everywhere', `${payload.revoked_count} sessions revoked`)
      await logout()
      navigate('/login', { replace: true })
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to revoke sessions'
      toast.error('Could not sign out everywhere', message)
    },
  })

  const sortedSessions = useMemo<UserSession[]>(() => {
    const sessions = sessionsQuery.data?.items ?? []
    return [...sessions].sort(
      (first, second) =>
        new Date(second.last_active_at).getTime() - new Date(first.last_active_at).getTime(),
    )
  }, [sessionsQuery.data?.items])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sessions"
        subtitle="Review active devices and revoke sessions you do not recognize."
        actions={
          <button
            type="button"
            className="btn-secondary inline-flex items-center gap-2"
            onClick={() => revokeAllSessionsMutation.mutate()}
            disabled={revokeAllSessionsMutation.isPending}
          >
            <LogOut className="h-4 w-4" />
            {revokeAllSessionsMutation.isPending ? 'Signing out...' : 'Sign out everywhere'}
          </button>
        }
      />

      <ProfileSettingsNav />

      <div className="surface-card rounded-2xl overflow-hidden">
        {sessionsQuery.isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-4 w-44" />
            <Skeleton className="h-4 w-56" />
            <Skeleton className="h-4 w-48" />
          </div>
        ) : sessionsQuery.isError ? (
          <div className="p-8 text-center">
            <ShieldAlert className="h-8 w-8 mx-auto text-rose-500 mb-2" />
            <p className="text-rose-600">Failed to load sessions.</p>
          </div>
        ) : sortedSessions.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>No active sessions found.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Device</th>
                <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">IP Address</th>
                <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Last Active</th>
                <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Created</th>
                <th className="text-right text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedSessions.map((session) => {
                const Icon = inferDeviceIcon(session.user_agent)
                return (
                  <tr key={session.id} className="border-b border-slate-100">
                    <td className="px-4 py-4">
                      <div className="flex items-start gap-2">
                        <Icon className="h-4 w-4 text-slate-500 mt-0.5" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-900">
                            {inferBrowserLabel(session.user_agent)}
                            {session.is_current && (
                              <span className="ml-2 pill bg-emerald-100 text-emerald-700 border-emerald-200">
                                Current
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-slate-500 truncate">
                            {session.user_agent || 'Unknown user agent'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {session.ip_address || 'Unknown'}
                    </td>
                    <td
                      className="px-4 py-4 text-sm text-slate-700"
                      title={new Date(session.last_active_at).toLocaleString()}
                    >
                      {formatRelativeTime(session.last_active_at)}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {new Date(session.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end">
                        <button
                          type="button"
                          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 disabled:opacity-60"
                          onClick={() => revokeSessionMutation.mutate(session.id)}
                          disabled={revokeSessionMutation.isPending || session.is_current}
                          title={session.is_current ? 'Use "Sign out everywhere" to end this session' : 'Revoke session'}
                        >
                          <Trash2 className="h-4 w-4" />
                          Revoke
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
