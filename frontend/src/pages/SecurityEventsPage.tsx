import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import ProfileSettingsNav from '@/components/ProfileSettingsNav'
import { TableSkeleton } from '@/components/skeletons'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import type { SecurityEvent } from '@/types'

const PAGE_SIZE = 100

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
    <div className="page-stack">
      <PageHeader
        title="Security Events"
        subtitle="Recent login and account-security activity for your account."
      />

      <ProfileSettingsNav />

      {securityEventsQuery.isLoading ? (
        <TableSkeleton rows={8} columns={4} />
      ) : securityEventsQuery.isError ? (
        <ErrorState
          title="Security events could not be loaded"
          message="We could not fetch your recent account activity."
          onRetry={() => void securityEventsQuery.refetch()}
        />
      ) : events.length === 0 ? (
        <EmptyState
          icon={<Activity className="h-8 w-8" aria-hidden="true" />}
          title="No security events found"
          description="Recent sign-ins and account-security changes will appear here."
        />
      ) : (
        <div className="space-y-4">
          <VirtualizedTable
            items={events}
            ariaLabel="Security events"
            columns={[
              { header: 'Event' },
              { header: 'IP Address' },
              { header: 'Date/Time' },
              { header: 'User Agent' },
            ]}
            gridTemplateColumns="minmax(14rem, 1.3fr) minmax(8rem, 0.8fr) minmax(10rem, 0.9fr) minmax(18rem, 1.4fr)"
            estimateRowHeight={72}
            rowKey={(event) => event.id}
            renderRow={(event: SecurityEvent) => (
              <>
                <div className="admin-table-cell text-sm capitalize text-slate-900 dark:text-slate-100">
                  {getEventLabel(event.event_type)}
                </div>
                <div className="admin-table-cell text-sm text-slate-700 dark:text-slate-300">
                  {event.ip_address || 'Unknown'}
                </div>
                <div className="admin-table-cell text-sm text-slate-700 dark:text-slate-300">
                  {formatDate(event.created_at)}
                </div>
                <div
                  className="admin-table-cell text-sm text-slate-700 dark:text-slate-300"
                  title={event.user_agent || undefined}
                >
                  {getAgentSnippet(event.user_agent)}
                </div>
              </>
            )}
          />

          <div className="surface-muted flex items-center justify-between px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
            <p>
              Page {data?.page ?? 1} of {totalPages || 1}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn-secondary px-3 py-1.5 text-sm"
                disabled={page <= 1}
                onClick={() => setPage((previous) => Math.max(previous - 1, 1))}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn-secondary px-3 py-1.5 text-sm"
                disabled={totalPages === 0 || page >= totalPages}
                onClick={() => setPage((previous) => previous + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
