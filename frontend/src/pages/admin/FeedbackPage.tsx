import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Link } from 'react-router-dom'
import {
  MessageSquare,
  Search,
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

const statusConfig: Record<FeedbackStatus, { label: string; icon: React.ReactNode; className: string }> = {
  pending: {
    label: 'Pending',
    icon: <Clock className="w-4 h-4" />,
    className: 'bg-yellow-100 text-yellow-700',
  },
  responded: {
    label: 'Responded',
    icon: <CheckCircle className="w-4 h-4" />,
    className: 'bg-green-100 text-green-700',
  },
  closed: {
    label: 'Closed',
    icon: <XCircle className="w-4 h-4" />,
    className: 'bg-gray-100 text-gray-700',
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
    className: 'text-red-600',
  },
  other: {
    label: 'Other',
    icon: <MoreHorizontal className="w-4 h-4" />,
    className: 'text-gray-600',
  },
}

export default function FeedbackPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<FeedbackStatus | ''>('')
  const [typeFilter, setTypeFilter] = useState<FeedbackType | ''>('')
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackDetailResponse | null>(null)
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()

  // Fetch feedback list
  const { data, isLoading } = useQuery({
    queryKey: ['feedback-management', page, statusFilter, typeFilter, search],
    queryFn: () =>
      api.getAllFeedback({
        page,
        per_page: 20,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
        search: search || undefined,
      }),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['feedback-stats'],
    queryFn: () => api.getManagementFeedbackStats(),
  })

  // Respond mutation
  const respondMutation = useMutation({
    mutationFn: ({ id, response }: { id: number; response: string }) =>
      api.respondToFeedback(id, response),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback-management'] })
      queryClient.invalidateQueries({ queryKey: ['feedback-stats'] })
      setSelectedFeedback(null)
    },
  })

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: FeedbackStatus }) =>
      api.updateFeedbackStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback-management'] })
      queryClient.invalidateQueries({ queryKey: ['feedback-stats'] })
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customer Feedback</h1>
          <p className="text-gray-600">Manage and respond to customer feedback</p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              </div>
              <MessageSquare className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-yellow-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-yellow-600">Pending</p>
                <p className="text-2xl font-bold text-yellow-700">{stats.pending}</p>
              </div>
              <Clock className="w-8 h-8 text-yellow-400" />
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-green-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600">Responded</p>
                <p className="text-2xl font-bold text-green-700">{stats.responded}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Closed</p>
                <p className="text-2xl font-bold text-gray-700">{stats.closed}</p>
              </div>
              <XCircle className="w-8 h-8 text-gray-400" />
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search feedback..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </form>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as FeedbackStatus | '')
                setPage(1)
              }}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading feedback...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No feedback found</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Customer
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Document
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Content
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.items.map((feedback) => (
                <tr key={feedback.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className={`flex items-center gap-2 ${typeConfig[feedback.feedback_type].className}`}>
                      {typeConfig[feedback.feedback_type].icon}
                      <span className="text-sm font-medium">
                        {typeConfig[feedback.feedback_type].label}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm">
                      <div className="flex items-center gap-1 text-gray-900">
                        <User className="w-3 h-3" />
                        {feedback.user_name}
                      </div>
                      {feedback.tenant_name && (
                        <div className="flex items-center gap-1 text-gray-500 text-xs mt-1">
                          <Building2 className="w-3 h-3" />
                          {feedback.tenant_name}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/documents/${feedback.document_id}`}
                      className="flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm"
                    >
                      <FileText className="w-3 h-3" />
                      {feedback.document_title.length > 30
                        ? `${feedback.document_title.slice(0, 30)}...`
                        : feedback.document_title}
                    </Link>
                  </td>
                  <td className="px-6 py-4 max-w-xs">
                    <p className="text-sm text-gray-700 truncate">
                      {feedback.content.length > 50
                        ? `${feedback.content.slice(0, 50)}...`
                        : feedback.content}
                    </p>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full ${
                        statusConfig[feedback.status].className
                      }`}
                    >
                      {statusConfig[feedback.status].icon}
                      {statusConfig[feedback.status].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(feedback.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setSelectedFeedback(feedback)}
                        className="text-blue-600 hover:text-blue-700 text-sm"
                      >
                        View
                      </button>
                      {feedback.status === 'pending' && (
                        <button
                          onClick={() => setSelectedFeedback(feedback)}
                          className="flex items-center gap-1 px-2 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                        >
                          <Send className="w-3 h-3" />
                          Respond
                        </button>
                      )}
                      {feedback.status === 'responded' && (
                        <button
                          onClick={() => {
                            if (confirm('Mark this feedback as closed?')) {
                              updateStatusMutation.mutate({ id: feedback.id, status: 'closed' })
                            }
                          }}
                          className="text-gray-600 hover:text-gray-800 text-sm"
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
        )}

        {/* Pagination */}
        {data && data.total > 20 && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Page {data.page} of {Math.ceil(data.total / data.per_page)}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.has_more}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
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
          onClose={() => setSelectedFeedback(null)}
          onRespond={(response) =>
            respondMutation.mutate({ id: selectedFeedback.id, response })
          }
          onUpdateStatus={(status) =>
            updateStatusMutation.mutate({ id: selectedFeedback.id, status })
          }
          isLoading={respondMutation.isPending || updateStatusMutation.isPending}
        />
      )}
    </div>
  )
}
