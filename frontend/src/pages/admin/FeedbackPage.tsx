import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Link, useSearchParams } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { SearchInput } from '@/components/form'
import { StatCardSkeleton, TableSkeleton } from '@/components/skeletons'
import {
  MessageSquare,
  Filter,
  HelpCircle,
  Lightbulb,
  AlertTriangle,
  MoreHorizontal,
  Clock,
  CheckCircle,
  XCircle,
  Send,
  Building2,
  User,
  FileText,
} from 'lucide-react'
import type { FeedbackDetailResponse, FeedbackStatus, FeedbackType } from '@/types'
import FeedbackResponseDialog from '@/components/FeedbackResponseDialog'
import { extractApiErrorMessage, useToast } from '@/lib/toast'

const statusConfig: Record<FeedbackStatus, { label: string; icon: React.ReactNode; className: string }> = {
  pending: {
    label: 'Pending',
    icon: <Clock className="w-4 h-4" />,
    className: 'bg-amber-100 text-amber-700',
  },
  responded: {
    label: 'Responded',
    icon: <CheckCircle className="w-4 h-4" />,
    className: 'bg-emerald-100 text-emerald-700',
  },
  closed: {
    label: 'Closed',
    icon: <XCircle className="w-4 h-4" />,
    className: 'bg-slate-100 text-slate-700',
  },
}

const typeConfig: Record<FeedbackType, { label: string; icon: React.ReactNode; className: string }> = {
  question: {
    label: 'Question',
    icon: <HelpCircle className="w-4 h-4" />,
    className: 'text-blue-600',
  },
  suggestion: {
    label: 'Suggestion',
    icon: <Lightbulb className="w-4 h-4" />,
    className: 'text-purple-600',
  },
  issue: {
    label: 'Issue',
    icon: <AlertTriangle className="w-4 h-4" />,
    className: 'text-rose-600',
  },
  other: {
    label: 'Other',
    icon: <MoreHorizontal className="w-4 h-4" />,
    className: 'text-slate-600',
  },
}

export default function FeedbackPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<FeedbackStatus | ''>('')
  const [typeFilter, setTypeFilter] = useState<FeedbackType | ''>('')
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackDetailResponse | null>(null)
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()
  const toast = useToast()
  const selectedFeedbackId = Number(searchParams.get('feedback') || '')

  const openFeedback = (feedback: FeedbackDetailResponse) => {
    setSelectedFeedback(feedback)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('feedback', String(feedback.id))
    setSearchParams(nextParams, { replace: true })
  }

  const closeFeedback = () => {
    setSelectedFeedback(null)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('feedback')
    setSearchParams(nextParams, { replace: true })
  }

  // Fetch feedback list
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['feedback-management', page, statusFilter, typeFilter, search],
    queryFn: () =>
      api.getAllFeedback({
        page,
        per_page: 20,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
        search: search || undefined,
      }),
    refetchInterval: 15000,
  })

  const feedbackDetailQuery = useQuery({
    queryKey: ['feedback-management-detail', selectedFeedbackId],
    queryFn: () => api.getFeedback(selectedFeedbackId),
    enabled: Number.isInteger(selectedFeedbackId) && selectedFeedbackId > 0,
  })

  useEffect(() => {
    if (feedbackDetailQuery.data) {
      setSelectedFeedback(feedbackDetailQuery.data)
    }
  }, [feedbackDetailQuery.data])

  // Fetch stats
  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['feedback-stats'],
    queryFn: () => api.getManagementFeedbackStats(),
    refetchInterval: 15000,
  })

  // Respond mutation
  const respondMutation = useMutation({
    mutationFn: ({ id, response }: { id: number; response: string }) =>
      api.respondToFeedback(id, response),
    onSuccess: (updatedFeedback) => {
      queryClient.invalidateQueries({ queryKey: ['feedback-management'] })
      queryClient.invalidateQueries({ queryKey: ['feedback-stats'] })
      setSelectedFeedback(updatedFeedback)
    },
  })

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: FeedbackStatus }) =>
      api.updateFeedbackStatus(id, status),
    onSuccess: (updatedFeedback) => {
      queryClient.invalidateQueries({ queryKey: ['feedback-management'] })
      queryClient.invalidateQueries({ queryKey: ['feedback-stats'] })
      setSelectedFeedback((current) =>
        current && current.id === updatedFeedback.id ? updatedFeedback : current,
      )
    },
  })

  const escalateMutation = useMutation({
    mutationFn: (feedbackId: number) => api.createSupportTicketFromFeedback(feedbackId),
    onSuccess: (ticket, feedbackId) => {
      queryClient.invalidateQueries({ queryKey: ['feedback-management'] })
      queryClient.invalidateQueries({ queryKey: ['supportTickets'] })
      queryClient.invalidateQueries({ queryKey: ['supportTicketSummary'] })
      setSelectedFeedback((current) =>
        current && current.id === feedbackId ? { ...current, ticket_id: ticket.id } : current,
      )
      toast.success('Escalated to Support')
    },
    onError: (error: unknown) => {
      toast.error(
        'Failed to escalate feedback',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  return (
    <div className="page-stack">
      <PageHeader
        title="Customer Feedback"
        subtitle="Review customer feedback and escalate specific items to Support when needed."
      />

      {/* Stats Cards */}
      {isStatsLoading ? (
        <StatCardSkeleton count={4} />
      ) : stats ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="surface-card rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-label">Total</p>
                <p className="metric-value">{stats.total}</p>
              </div>
              <MessageSquare className="w-8 h-8 text-slate-400" />
            </div>
          </div>
          <div className="surface-card rounded-2xl border-amber-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-label text-amber-600 dark:text-amber-300">Pending</p>
                <p className="metric-value text-amber-700 dark:text-amber-200">{stats.pending}</p>
              </div>
              <Clock className="w-8 h-8 text-amber-400" />
            </div>
          </div>
          <div className="surface-card rounded-2xl border-emerald-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-label text-emerald-600 dark:text-emerald-300">Responded</p>
                <p className="metric-value text-emerald-700 dark:text-emerald-200">{stats.responded}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            </div>
          </div>
          <div className="surface-card rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-label">Closed</p>
                <p className="metric-value text-slate-700 dark:text-slate-200">{stats.closed}</p>
              </div>
              <XCircle className="w-8 h-8 text-slate-400" />
            </div>
          </div>
        </div>
      ) : null}

      {/* Filters */}
      <div className="surface-card rounded-2xl p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <SearchInput
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              onClear={() => {
                setSearch('')
                setPage(1)
              }}
              placeholder="Search feedback..."
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as FeedbackStatus | '')
                setPage(1)
              }}
              className="select-field"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="responded">Responded</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value as FeedbackType | '')
              setPage(1)
            }}
            className="select-field"
          >
            <option value="">All Types</option>
            <option value="question">Question</option>
            <option value="suggestion">Suggestion</option>
            <option value="issue">Issue</option>
            <option value="other">Other</option>
          </select>
        </div>
      </div>

      {/* Feedback Table */}
      <div className="surface-card rounded-2xl overflow-hidden">
        {isLoading ? (
          <TableSkeleton rows={6} columns={7} />
        ) : isError ? (
          <div className="p-6">
            <ErrorState
              title="Feedback could not be loaded"
              message="We could not fetch the customer feedback queue."
              onRetry={() => void refetch()}
            />
          </div>
        ) : !data?.items?.length ? (
          <div className="p-6">
            <EmptyState
              icon={<MessageSquare className="h-8 w-8" aria-hidden="true" />}
              title="No feedback found"
              description="Try changing the filters or search terms to widen the results."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Customer
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Document
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Content
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Date
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {data.items.map((feedback) => (
                <tr key={feedback.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className={`flex items-center gap-1.5 ${typeConfig[feedback.feedback_type].className}`}>
                      {typeConfig[feedback.feedback_type].icon}
                      <span className="text-sm font-medium">
                        {typeConfig[feedback.feedback_type].label}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">
                      <div className="card-title flex items-center gap-1 whitespace-nowrap">
                        <User className="w-3 h-3 flex-shrink-0" />
                        {feedback.user_name}
                      </div>
                      {feedback.tenant_name && (
                        <div className="helper-copy mt-0.5 flex items-center gap-1 whitespace-nowrap">
                          <Building2 className="w-3 h-3 flex-shrink-0" />
                          {feedback.tenant_name}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/documents/${feedback.document_id}/fullscreen`}
                      className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                    >
                      <FileText className="w-3 h-3 flex-shrink-0" />
                      <span className="max-w-[10rem] truncate">
                        {feedback.document_title}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <p className="body-copy max-w-[14rem] truncate">
                      {feedback.content}
                    </p>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`pill flex items-center gap-1 ${
                        statusConfig[feedback.status].className
                      }`}
                    >
                      {statusConfig[feedback.status].icon}
                      {statusConfig[feedback.status].label}
                    </span>
                  </td>
                  <td className="px-4 py-3 body-copy whitespace-nowrap">
                    {new Date(feedback.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => openFeedback(feedback)}
                        className="btn-secondary table-action-btn"
                      >
                        View
                      </button>
                      {feedback.ticket_id ? (
                        <Link
                          to={`/support?ticket=${feedback.ticket_id}`}
                          className="btn-secondary table-action-btn"
                          title="Open Support Conversation"
                        >
                          Support
                        </Link>
                      ) : null}
                      {feedback.status === 'pending' && (
                        <button
                          type="button"
                          onClick={() => openFeedback(feedback)}
                          className="btn-primary table-action-btn"
                        >
                          <Send className="w-3 h-3" />
                          Respond
                        </button>
                      )}
                      {feedback.status === 'responded' && (
                        <button
                          type="button"
                          onClick={() => {
                            if (confirm('Mark this feedback as closed?')) {
                              updateStatusMutation.mutate({ id: feedback.id, status: 'closed' })
                            }
                          }}
                          className="btn-ghost table-action-btn"
                        >
                          Close
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total > 20 && (
          <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-3">
            <p className="body-copy">
              Page {data.page} of {Math.ceil(data.total / data.per_page)}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-ghost table-action-btn disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.has_more}
                className="btn-ghost table-action-btn disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Response Dialog */}
      {selectedFeedback && (
        <FeedbackResponseDialog
          feedback={selectedFeedback}
          onClose={closeFeedback}
          onRespond={(response) =>
            respondMutation.mutate({ id: selectedFeedback.id, response })
          }
          onUpdateStatus={(status) =>
            updateStatusMutation.mutate({ id: selectedFeedback.id, status })
          }
          onEscalate={() => escalateMutation.mutate(selectedFeedback.id)}
          isLoading={
            respondMutation.isPending ||
            updateStatusMutation.isPending ||
            escalateMutation.isPending
          }
        />
      )}
    </div>
  )
}
