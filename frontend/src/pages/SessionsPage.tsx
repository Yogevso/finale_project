import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Laptop, LogOut, MonitorSmartphone, Smartphone, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import ProfileSettingsNav from '@/components/ProfileSettingsNav'
import { TableSkeleton } from '@/components/skeletons'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDate } from '@/lib/dateUtils'
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
  return formatDate(isoDateTime)
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
    <div className="page-stack">
      <PageHeader
        title="Sessions"
        subtitle="Review active devices and revoke sessions you do not recognize."
        actions={
          <button
            type="button"
            className="btn-secondary table-action-btn disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={() => revokeAllSessionsMutation.mutate()}
            disabled={revokeAllSessionsMutation.isPending}
          >
            <LogOut className="h-4 w-4" />
            {revokeAllSessionsMutation.isPending ? 'Signing out...' : 'Sign out everywhere'}
          </button>
        }
      />

      <ProfileSettingsNav />

      {sessionsQuery.isLoading ? (
        <TableSkeleton rows={6} columns={5} />
      ) : sessionsQuery.isError ? (
        <ErrorState
          title="Sessions could not be loaded"
          message="We could not fetch your recent device activity."
          onRetry={() => void sessionsQuery.refetch()}
        />
      ) : sortedSessions.length === 0 ? (
        <EmptyState
          icon={<Laptop className="h-8 w-8" aria-hidden="true" />}
          title="No active sessions found"
          description="This account does not have any active sessions to review right now."
        />
      ) : (
        <VirtualizedTable
          items={sortedSessions}
          ariaLabel="Active sessions"
          columns={[
            { header: 'Device' },
            { header: 'IP Address' },
            { header: 'Last Active' },
            { header: 'Created' },
            { header: 'Actions', headerClassName: 'text-right' },
          ]}
          gridTemplateColumns="minmax(18rem, 2.2fr) minmax(8rem, 1fr) minmax(8rem, 0.9fr) minmax(8rem, 0.9fr) minmax(9rem, 0.8fr)"
          estimateRowHeight={88}
          rowKey={(session) => session.id}
          renderRow={(session) => {
            const Icon = inferDeviceIcon(session.user_agent)

            return (
              <>
                <div className="admin-table-cell">
                  <div className="flex items-start gap-2">
                    <Icon className="mt-0.5 h-4 w-4 text-slate-500" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {inferBrowserLabel(session.user_agent)}
                        {session.is_current ? (
                          <span className="ml-2 pill border-emerald-200 bg-emerald-100 text-emerald-700">
                            Current
                          </span>
                        ) : null}
                      </p>
                      <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                        {session.user_agent || 'Unknown user agent'}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="admin-table-cell text-sm text-slate-700 dark:text-slate-300">
                  {session.ip_address || 'Unknown'}
                </div>
                <div
                  className="admin-table-cell text-sm text-slate-700 dark:text-slate-300"
                  title={formatDate(session.last_active_at)}
                >
                  {formatRelativeTime(session.last_active_at)}
                </div>
                <div className="admin-table-cell text-sm text-slate-700 dark:text-slate-300">
                  {formatDate(session.created_at)}
                </div>
                <div className="admin-table-cell">
                  <div className="flex justify-end">
                    <button
                      type="button"
                      className="btn-danger px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                      onClick={() => revokeSessionMutation.mutate(session.id)}
                      disabled={revokeSessionMutation.isPending || session.is_current}
                      title={session.is_current ? 'Use "Sign out everywhere" to end this session' : 'Revoke session'}
                    >
                      <Trash2 className="h-4 w-4" />
                      Revoke
                    </button>
                  </div>
                </div>
              </>
            )
          }}
        />
      )}
    </div>
  )
}
