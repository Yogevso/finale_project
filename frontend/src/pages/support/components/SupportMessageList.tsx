import { formatDistanceToNow } from 'date-fns'
import { Eye, Paperclip, X } from 'lucide-react'

import type { SupportTicketDetail } from '@/types/chat'

import { formatSupportFileSize } from '../constants'

interface SupportMessageListProps {
  ticket: SupportTicketDetail
  currentUserId?: number
  otherViewerCount: number
  onUnassignAgent: (agentId: number) => void
  onUpdatePriority: (priority: SupportTicketDetail['priority']) => void
  onUpdateStatus: (status: SupportTicketDetail['status']) => void
}

export function SupportMessageList({
  ticket,
  currentUserId,
  otherViewerCount,
  onUnassignAgent,
  onUpdatePriority,
  onUpdateStatus,
}: SupportMessageListProps) {
  return (
    <>
      <div className="surface-card flex flex-wrap items-center gap-3 rounded-xl p-3">
        <label
          htmlFor="ticket-status"
          className="text-xs font-medium text-gray-500 dark:text-slate-400"
        >
          Status:
        </label>
        <select
          id="ticket-status"
          value={ticket.status}
          onChange={(event) => onUpdateStatus(event.target.value as SupportTicketDetail['status'])}
          className="select-field w-auto min-w-[9rem]"
        >
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>

        <label
          htmlFor="ticket-priority"
          className="ml-4 text-xs font-medium text-gray-500 dark:text-slate-400"
        >
          Priority:
        </label>
        <select
          id="ticket-priority"
          value={ticket.priority}
          onChange={(event) =>
            onUpdatePriority(event.target.value as SupportTicketDetail['priority'])
          }
          className="select-field w-auto min-w-[9rem]"
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>

        {ticket.assignments.length > 0 ? (
          <div className="ml-auto flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
            <span>Assigned:</span>
            {ticket.assignments.map((assignment) => (
              <span
                key={assignment.id}
                className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2 py-0.5 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200"
              >
                {assignment.agent_full_name || `Agent #${assignment.agent_id}`}
                {assignment.is_primary ? (
                  <span className="text-[9px] text-sky-500 dark:text-sky-300">(primary)</span>
                ) : null}
                <button
                  type="button"
                  onClick={() => onUnassignAgent(assignment.agent_id)}
                  className="ml-0.5 rounded-full p-0.5 text-sky-400 hover:bg-sky-100 hover:text-sky-700 dark:text-sky-300 dark:hover:bg-sky-900/40 dark:hover:text-sky-100"
                  title="Unassign"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        ) : null}

        {otherViewerCount > 0 ? (
          <div className="flex items-center gap-1.5 text-xs text-emerald-600">
            <Eye className="h-3.5 w-3.5" />
            <span>
              {otherViewerCount} other agent{otherViewerCount > 1 ? 's' : ''} viewing
            </span>
          </div>
        ) : null}
      </div>

      <div className="surface-card rounded-xl">
        <div className="max-h-[50vh] space-y-3 overflow-y-auto p-4">
          {ticket.messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender_id === currentUserId ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                  message.is_internal_note
                    ? 'border border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-100'
                    : message.sender_id === currentUserId
                      ? 'bg-sky-600 text-white'
                      : 'bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-slate-100'
                }`}
              >
                <div className="mb-0.5 flex items-center gap-1.5 text-xs opacity-75">
                  <span className="font-medium">{message.sender_full_name || 'Unknown'}</span>
                  {message.is_internal_note ? (
                    <span className="italic">(internal note)</span>
                  ) : null}
                </div>
                {message.content ? (
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                ) : null}
                {message.file_name ? (
                  message.file_url ? (
                    <a
                      href={message.file_url}
                      className={`mt-2 flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                        message.is_internal_note
                          ? 'border-amber-300 bg-amber-100/70 text-amber-950 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100'
                          : message.sender_id === currentUserId
                            ? 'border-sky-400/40 bg-sky-500/10 text-white'
                            : 'border-slate-200 bg-white/70 text-slate-900 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-100'
                      }`}
                    >
                      <Paperclip className="h-4 w-4 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{message.file_name}</span>
                      <span className="shrink-0 text-xs opacity-75">
                        {formatSupportFileSize(message.file_size)}
                      </span>
                    </a>
                  ) : (
                    <div
                      className={`mt-2 flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                        message.is_internal_note
                          ? 'border-amber-300 bg-amber-100/70 text-amber-950 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100'
                          : message.sender_id === currentUserId
                            ? 'border-sky-400/40 bg-sky-500/10 text-white'
                            : 'border-slate-200 bg-white/70 text-slate-900 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-100'
                      }`}
                    >
                      <Paperclip className="h-4 w-4 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{message.file_name}</span>
                      <span className="shrink-0 text-xs opacity-75">Uploading...</span>
                    </div>
                  )
                ) : null}
                <p className="mt-1 text-[10px] opacity-60">
                  {formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
