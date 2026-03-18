import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ShieldAlert } from 'lucide-react'

import PageHeader from '@/components/PageHeader'
import ProfileSettingsNav from '@/components/ProfileSettingsNav'
import Skeleton from '@/components/Skeleton'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import type { SecurityEvent } from '@/types'

const PAGE_SIZE = 20

const EVENT_TYPE_LABELS: Record<string, string> = {
  login: 'Successful login',
  new_device_login: 'Login from new device',
  password_changed: 'Password changed',
  password_reset: 'Password reset',
  session_revoked: 'Session revoked',
  sessions_revoked_all: 'Signed out everywhere',
}

function getEventLabel(eventType: string): string {
  return EVENT_TYPE_LABELS[eventType] ?? eventType.replace(/_/g, ' ')
}

function getAgentSnippet(userAgent: string | null | undefined): string {
  if (!userAgent) return 'Unknown user agent'
  if (userAgent.length <= 100) return userAgent
  return `${userAgent.slice(0, 97)}...`
}

export default function SecurityEventsPage() {
  const [page, setPage] = useState(1)

  const securityEventsQuery = useQuery({
    queryKey: ['security-events', page],
    queryFn: () => api.getMySecurityEvents({ page, page_size: PAGE_SIZE }),
  })

  const data = securityEventsQuery.data
  const events = data?.items ?? []
  const totalPages = data?.total_pages ?? 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security Events"
        subtitle="Recent login and account-security activity for your account."
      />

      <ProfileSettingsNav />

      <div className="surface-card rounded-2xl overflow-hidden">
        {securityEventsQuery.isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-4 w-44" />
            <Skeleton className="h-4 w-56" />
            <Skeleton className="h-4 w-48" />
          </div>
        ) : securityEventsQuery.isError ? (
          <div className="p-8 text-center">
            <ShieldAlert className="h-8 w-8 mx-auto text-rose-500 mb-2" />
            <p className="text-rose-600">Failed to load security events.</p>
          </div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>No security events found.</p>
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Event</th>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">IP Address</th>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Date/Time</th>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">User Agent</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event: SecurityEvent) => (
                  <tr key={event.id} className="border-b border-slate-100">
                    <td className="px-4 py-4 text-sm text-slate-900 capitalize">
                      {getEventLabel(event.event_type)}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {event.ip_address || 'Unknown'}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {formatDate(event.created_at)}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700" title={event.user_agent || undefined}>
                      {getAgentSnippet(event.user_agent)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-sm">
              <p className="text-slate-600">
                Page {data?.page ?? 1} of {totalPages || 1}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={page <= 1}
                  onClick={() => setPage((previous) => Math.max(previous - 1, 1))}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={totalPages === 0 || page >= totalPages}
                  onClick={() => setPage((previous) => previous + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
