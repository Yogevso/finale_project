/**
 * CustomerSupportPage - customer portal support tickets (X1-088 to X1-092)
 */

import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { ListSkeleton, MessageSkeleton } from '@/components/skeletons'
import { useSupportSocket } from '@/hooks/useSupportSocket'
import { ATTACHMENT_INPUT_ACCEPT, validateAttachmentFile } from '@/lib/attachmentUpload'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, Paperclip, Plus, Send, X } from 'lucide-react'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type {
  SupportTicket,
  SupportTicketDetail,
  SupportTicketMessage,
  SupportTicketPriority,
} from '@/types/chat'

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-200',
  in_progress: 'bg-sky-100 text-sky-800 dark:bg-sky-950/50 dark:text-sky-200',
  resolved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200',
  closed: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
}

const PRIORITY_COLORS: Record<string, string> = {
  low: 'text-slate-500 dark:text-slate-400',
  normal: 'text-sky-600 dark:text-sky-300',
  high: 'text-orange-600 dark:text-orange-300',
  urgent: 'text-red-600 dark:text-red-300',
}

function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes || bytes < 1024) {
    return `${bytes ?? 0} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function CustomerSupportPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const prefillSubject = searchParams.get('subject') || ''
  const prefillContent = searchParams.get('content') || ''

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setShowCreate(true)
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const ticketsQuery = useQuery({
    queryKey: ['myTickets'],
    queryFn: () => api.getMyTickets(),
  })

  const ticketQuery = useQuery({
    queryKey: ['myTicket', activeTicketId],
    queryFn: () => (activeTicketId ? api.getMyTicket(activeTicketId) : Promise.reject()),
    enabled: !!activeTicketId,
  })

  useSupportSocket({
    activeTicketId,
    onNewMessage: (message) => {
      void queryClient.invalidateQueries({ queryKey: ['myTickets'] })
      if (message.ticket_id === activeTicketId) {
        void queryClient.invalidateQueries({ queryKey: ['myTicket', activeTicketId] })
      }
    },
    onStatusUpdate: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['myTickets'] })
      if (data.ticket_id === activeTicketId) {
        void queryClient.invalidateQueries({ queryKey: ['myTicket', activeTicketId] })
      }
    },
  })

  const tickets = ticketsQuery.data?.items ?? []

  if (activeTicketId && ticketQuery.isLoading) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="Customer Portal"
          title="Support"
          subtitle="Get help from our team"
        />
        <MessageSkeleton rows={4} />
      </div>
    )
  }

  if (activeTicketId && ticketQuery.isError) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="Customer Portal"
          title="Support"
          subtitle="Get help from our team"
        />
        <ErrorState
          title="Ticket could not be loaded"
          message="We could not load this support conversation."
          onRetry={() => void ticketQuery.refetch()}
        />
      </div>
    )
  }

  if (activeTicketId && ticketQuery.data) {
    return (
      <div className="animate-fade-in">
        <CustomerTicketView
          ticket={ticketQuery.data}
          onBack={() => setActiveTicketId(null)}
        />
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Customer Portal"
        title="Support"
        subtitle="Get help from our team"
        actions={
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary table-action-btn"
            type="button"
          >
            <Plus className="h-4 w-4" /> New Ticket
          </button>
        }
      />

      {ticketsQuery.isLoading ? (
        <ListSkeleton rows={4} />
      ) : ticketsQuery.isError ? (
        <ErrorState
          title="Support tickets unavailable"
          message="We could not load your support tickets."
          onRetry={() => void ticketsQuery.refetch()}
        />
      ) : tickets.length === 0 ? (
        <EmptyState
          title="No support tickets yet"
          description="Create a ticket to start a conversation with our support team."
          action={{ label: 'Create Ticket', onClick: () => setShowCreate(true) }}
        />
      ) : (
        <div className="space-y-3">
          {tickets.map((ticket: SupportTicket) => (
            <button
              key={ticket.id}
              type="button"
              onClick={() => setActiveTicketId(ticket.id)}
              className="surface-card w-full rounded-xl p-4 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/70"
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <p className="card-title">{ticket.subject}</p>
                  <p className="helper-copy mt-1">
                    #{ticket.id} - {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`helper-copy font-medium ${PRIORITY_COLORS[ticket.priority]}`}>
                    {ticket.priority}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[ticket.status]}`}>
                    {ticket.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateTicketModal
          initialSubject={prefillSubject}
          initialContent={prefillContent}
          onClose={() => setShowCreate(false)}
          onCreate={() => {
            setShowCreate(false)
            void queryClient.invalidateQueries({ queryKey: ['myTickets'] })
          }}
        />
      )}
    </div>
  )
}

function CustomerTicketView({
  ticket,
  onBack,
}: {
  ticket: SupportTicketDetail
  onBack: () => void
}) {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [message, setMessage] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const toast = useToast()
  const optimisticIdCounter = useRef(0)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const canSend = Boolean(message.trim() || selectedFile)

  const sendMutation = useMutation({
    mutationFn: (request: { content: string; file: File | null }) =>
      api.sendMyTicketMessage(ticket.id, request),
    onMutate: async (request: { content: string; file: File | null }) => {
      await queryClient.cancelQueries({ queryKey: ['myTicket', ticket.id] })
      const previous = queryClient.getQueryData<SupportTicketDetail>(['myTicket', ticket.id])
      const draftMessage = request.content
      const draftFile = request.file

      if (currentUser && previous) {
        optimisticIdCounter.current -= 1
        const optimistic: SupportTicketMessage = {
          id: optimisticIdCounter.current,
          ticket_id: ticket.id,
          sender_id: currentUser.id,
          sender_type: 'customer',
          content: draftMessage,
          is_internal_note: false,
          file_url: null,
          file_name: draftFile?.name ?? null,
          file_size: draftFile?.size ?? null,
          file_mime_type: draftFile?.type ?? null,
          created_at: new Date().toISOString(),
          sender_full_name: currentUser.full_name,
        }
        queryClient.setQueryData<SupportTicketDetail>(['myTicket', ticket.id], {
          ...previous,
          messages: [...previous.messages, optimistic],
        })
      }

      setMessage('')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      return { previous, draftMessage, draftFile }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['myTicket', ticket.id] })
      void queryClient.invalidateQueries({ queryKey: ['myTickets'] })
    },
    onError: (error: unknown, _request, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['myTicket', ticket.id], context.previous)
      }
      setMessage(context?.draftMessage ?? '')
      setSelectedFile(context?.draftFile ?? null)
      toast.error('Failed to send reply', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const closeMutation = useMutation({
    mutationFn: () => api.closeMyTicket(ticket.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['myTicket', ticket.id] })
      void queryClient.invalidateQueries({ queryKey: ['myTickets'] })
      toast.success('Ticket closed')
    },
    onError: (error: unknown) => {
      toast.error('Failed to close ticket', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const canClose = ticket.status === 'open' || ticket.status === 'resolved'

  const handleSelectedFile = (file: File | null) => {
    if (!file) {
      setSelectedFile(null)
      return
    }
    const validationError = validateAttachmentFile(file)
    if (validationError) {
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      toast.error('Attachment rejected', validationError)
      return
    }
    setSelectedFile(file)
  }

  const handleSend = () => {
    if (!canSend) {
      return
    }
    sendMutation.mutate({ content: message.trim(), file: selectedFile })
  }

  return (
    <div className="page-stack">
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="btn-icon h-9 w-9"
          type="button"
          aria-label="Back to support tickets"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="section-title">{ticket.subject}</h2>
          <div className="helper-copy flex items-center gap-2">
            <span>#{ticket.id}</span>
            <span className={`rounded-full px-2 py-0.5 font-medium ${STATUS_COLORS[ticket.status]}`}>
              {ticket.status.replace('_', ' ')}
            </span>
          </div>
        </div>
        {canClose && (
          <button
            onClick={() => closeMutation.mutate()}
            disabled={closeMutation.isPending}
            className="btn-secondary table-action-btn"
            type="button"
          >
            Close Ticket
          </button>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="max-h-[60vh] space-y-4 overflow-y-auto p-4">
          {ticket.messages.filter((m) => !m.is_internal_note).length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400 dark:text-slate-500">
              <Send className="mb-2 h-8 w-8" />
              <p className="card-title text-slate-500 dark:text-slate-300">No messages yet</p>
              <p className="helper-copy mt-0.5">Send a message to start the conversation</p>
            </div>
          ) : (
            ticket.messages
              .filter((m) => !m.is_internal_note)
              .map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender_type === 'customer' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                      msg.sender_type === 'customer'
                        ? 'bg-sky-600 text-white'
                        : 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                    }`}
                  >
                    {msg.sender_type === 'agent' && (
                      <p className="mb-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">
                        {msg.sender_full_name || 'Support Agent'}
                      </p>
                    )}
                    {msg.content ? <p className="whitespace-pre-wrap text-sm">{msg.content}</p> : null}
                    {msg.file_name ? (
                      msg.file_url ? (
                        <a
                          href={msg.file_url}
                          className={`mt-2 flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                            msg.sender_type === 'customer'
                              ? 'border-sky-400/40 bg-sky-500/10 text-white'
                              : 'border-slate-200 bg-white/70 text-slate-900 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-100'
                          }`}
                        >
                          <Paperclip className="h-4 w-4 shrink-0" />
                          <span className="min-w-0 flex-1 truncate">{msg.file_name}</span>
                          <span className="shrink-0 text-xs opacity-75">{formatFileSize(msg.file_size)}</span>
                        </a>
                      ) : (
                        <div
                          className={`mt-2 flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                            msg.sender_type === 'customer'
                              ? 'border-sky-400/40 bg-sky-500/10 text-white'
                              : 'border-slate-200 bg-white/70 text-slate-900 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-100'
                          }`}
                        >
                          <Paperclip className="h-4 w-4 shrink-0" />
                          <span className="min-w-0 flex-1 truncate">{msg.file_name}</span>
                          <span className="shrink-0 text-xs opacity-75">Uploading...</span>
                        </div>
                      )
                    ) : null}
                    <p
                      className={`mt-1 text-[10px] ${
                        msg.sender_type === 'customer'
                          ? 'text-sky-200'
                          : 'text-slate-400 dark:text-slate-500'
                      }`}
                    >
                      {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))
          )}
        </div>

        {ticket.status !== 'closed' && (
          <div className="space-y-3 border-t border-slate-200 p-3 dark:border-slate-800">
            {selectedFile ? (
              <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800/60">
                <Paperclip className="h-4 w-4 shrink-0 text-slate-500 dark:text-slate-300" />
                <span className="min-w-0 flex-1 truncate">{selectedFile.name}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {formatFileSize(selectedFile.size)}
                </span>
                <button
                  type="button"
                  className="btn-icon h-7 w-7"
                  aria-label="Remove attachment"
                  onClick={() => {
                    setSelectedFile(null)
                    if (fileInputRef.current) {
                      fileInputRef.current.value = ''
                    }
                  }}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : null}

            <div className="flex items-end gap-2">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="Type your reply..."
                rows={1}
                className="input-field flex-1 resize-none"
              />
              <label
                className="btn-secondary flex h-9 w-9 cursor-pointer items-center justify-center rounded-full p-0"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ATTACHMENT_INPUT_ACCEPT}
                  aria-label="Attach a file"
                  className="sr-only"
                  onChange={(e) => handleSelectedFile(e.target.files?.[0] ?? null)}
                />
                <Paperclip className="h-4 w-4" />
              </label>
              <button
                onClick={handleSend}
                disabled={sendMutation.isPending || !canSend}
                className="btn-primary h-9 w-9 rounded-full p-0 disabled:opacity-50"
                type="button"
                aria-label="Send reply"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function CreateTicketModal({
  initialSubject = '',
  initialContent = '',
  onClose,
  onCreate,
}: {
  initialSubject?: string
  initialContent?: string
  onClose: () => void
  onCreate: () => void
}) {
  const [subject, setSubject] = useState(initialSubject)
  const [content, setContent] = useState(initialContent)
  const [priority, setPriority] = useState<SupportTicketPriority>('normal')

  const createMutation = useMutation({
    mutationFn: () => api.createMyTicket({ subject, content, priority }),
    onSuccess: onCreate,
  })

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <div className="modal-content w-full max-w-md">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h2 className="section-title">New Support Ticket</h2>
          <button
            onClick={onClose}
            className="btn-icon h-9 w-9"
            type="button"
            aria-label="Close new support ticket dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4 p-6">
          <div>
            <label
              htmlFor="customer-ticket-subject"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Subject
            </label>
            <input
              id="customer-ticket-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="input-field"
              placeholder="Brief description of your issue"
            />
          </div>
          <div>
            <label
              htmlFor="customer-ticket-priority"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Priority
            </label>
            <select
              id="customer-ticket-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as SupportTicketPriority)}
              className="select-field"
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="customer-ticket-description"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Description
            </label>
            <textarea
              id="customer-ticket-description"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              className="input-field"
              placeholder="Describe your issue in detail..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-4 dark:border-slate-800">
          <button onClick={onClose} className="btn-secondary table-action-btn" type="button">
            Cancel
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || !subject.trim() || !content.trim()}
            className="btn-primary table-action-btn disabled:opacity-50"
            type="button"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </div>
    </div>
  )
}
