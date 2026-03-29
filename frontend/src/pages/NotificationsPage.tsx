import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Bell,
  Check,
  CheckCheck,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Mail,
  MessageSquare,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import ConfirmationDialog from '@/components/ConfirmationDialog'
import { TableSkeleton } from '@/components/skeletons'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import {
  deleteReadNotifications,
  markAllNotificationsRead,
  NOTIFICATIONS_QUERY_KEY,
  removeNotification,
  setNotificationReadState,
} from '@/lib/notificationsCache'
import { useToast } from '@/lib/toast'
import type { Notification, NotificationListResponse, NotificationType } from '@/types'

const NOTIFICATIONS_PAGE_SIZE = 20

const getNotificationIcon = (type: NotificationType) => {
  switch (type) {
    case 'comment_added':
    case 'comment_reply':
      return <MessageSquare className="w-4 h-4 text-sky-500" />
    case 'document_created':
    case 'document_updated':
    case 'document_published':
    case 'version_published':
      return <FileText className="w-4 h-4 text-emerald-500" />
    case 'review_submitted':
    case 'review_approved':
    case 'review_rejected':
    case 'review_reminder':
    case 'review_escalated':
      return <ClipboardCheck className="w-4 h-4 text-amber-500" />
    case 'feedback_received':
    case 'feedback_responded':
    case 'ticket_new_customer_msg':
    case 'ticket_mention':
    case 'ticket_handoff':
      return <MessageSquare className="w-4 h-4 text-indigo-500" />
    case 'system':
    default:
      return <AlertCircle className="w-4 h-4 text-slate-500" />
  }
}

const formatTime = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(dateString)
}

export default function NotificationsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const hasMounted = useRef(false)
  const currentLimit = page * NOTIFICATIONS_PAGE_SIZE
  const toast = useToast()
  const [confirmAction, setConfirmAction] = useState<{ title: string; description: string; onConfirm: () => void } | null>(null)

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: NOTIFICATIONS_QUERY_KEY,
    queryFn: () => api.getNotifications(false, currentLimit),
  })

  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true
      return
    }
    void refetch()
  }, [currentLimit, refetch])

  const notifications = data?.items || []
  const unreadCount = data?.unread_count || 0
  const hasMore = (data?.total || 0) > notifications.length

  const markReadMutation = useMutation({
    mutationFn: (notificationId: number) => api.markNotificationRead(notificationId),
    onMutate: async (notificationId) => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
      const previous = queryClient.getQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY)
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (current) =>
        setNotificationReadState(current, notificationId, true),
      )
      return { previous }
    },
    onError: (_error, _notificationId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, context.previous)
      }
      toast.error('Could not mark notification as read')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
    },
  })

  const markUnreadMutation = useMutation({
    mutationFn: (notificationId: number) => api.markNotificationUnread(notificationId),
    onMutate: async (notificationId) => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
      const previous = queryClient.getQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY)
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (current) =>
        setNotificationReadState(current, notificationId, false),
      )
      return { previous }
    },
    onError: (_error, _notificationId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, context.previous)
      }
      toast.error('Could not mark notification as unread')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (notificationId: number) => api.deleteNotification(notificationId),
    onMutate: async (notificationId) => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
      const previous = queryClient.getQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY)
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (current) =>
        removeNotification(current, notificationId),
      )
      return { previous }
    },
    onError: (_error, _notificationId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, context.previous)
      }
      toast.error('Could not delete notification')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => api.markAllNotificationsRead(),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
      const previous = queryClient.getQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY)
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (current) =>
        markAllNotificationsRead(current),
      )
      return { previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, context.previous)
      }
      toast.error('Could not mark all notifications as read')
    },
    onSuccess: () => {
      toast.success('All notifications marked as read')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
    },
  })

  const deleteReadMutation = useMutation({
    mutationFn: () => api.deleteAllNotifications(true),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
      const previous = queryClient.getQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY)
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (current) =>
        deleteReadNotifications(current),
      )
      return { previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, context.previous)
      }
      toast.error('Could not delete read notifications')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
    },
  })

  const openNotificationLink = (notification: Notification) => {
    if (!notification.link) return
    const link = notification.link
    if (link.startsWith('http://') || link.startsWith('https://')) {
      window.open(link, '_blank', 'noopener,noreferrer')
      return
    }
    navigate(link)
  }

  const hasReadNotifications = notifications.some((item) => item.is_read)
  const anyActionPending =
    markReadMutation.isPending ||
    markUnreadMutation.isPending ||
    deleteMutation.isPending ||
    markAllReadMutation.isPending ||
    deleteReadMutation.isPending
  const notificationColumns = [
    { header: 'Status' },
    { header: 'Notification' },
    { header: 'Received' },
    { header: 'Actions', headerClassName: 'text-right' },
  ]

  return (
    <div className="page-stack">
      <PageHeader
        title="Notifications"
        subtitle="Review updates and manage read status."
        meta={
          <span className="pill border-sky-200 bg-sky-100 text-sky-800 dark:border-sky-900/70 dark:bg-sky-950/40 dark:text-sky-200">
            {unreadCount} unread
          </span>
        }
        actions={
          <>
            <button
              type="button"
              onClick={() => void refetch()}
              className="btn-ghost table-action-btn"
              disabled={isFetching}
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => markAllReadMutation.mutate()}
                className="btn-secondary table-action-btn"
                disabled={anyActionPending}
              >
                <CheckCheck className="w-4 h-4" />
                Mark all read
              </button>
            )}
            {hasReadNotifications && (
              <button
                type="button"
                onClick={() => {
                  setConfirmAction({
                    title: 'Delete read notifications',
                    description: 'Are you sure you want to delete all read notifications? This cannot be undone.',
                    onConfirm: () => { deleteReadMutation.mutate(); setConfirmAction(null) },
                  })
                }}
                className="btn-danger table-action-btn"
                disabled={anyActionPending}
              >
                <Trash2 className="w-4 h-4" />
                Delete read
              </button>
            )}
          </>
        }
      />

      <div className="surface-card rounded-2xl overflow-hidden">
        {isLoading ? (
          <TableSkeleton rows={8} columns={4} />
        ) : isError ? (
          <ErrorState
            title="Notifications could not be loaded"
            message="We could not fetch your latest updates right now."
            onRetry={() => void refetch()}
            className="p-10"
          />
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={<Bell className="h-10 w-10" aria-hidden="true" />}
            title="No notifications yet"
            description="New activity, review updates, and document events will appear here."
            className="p-12"
          />
        ) : (
          <>
            <VirtualizedTable
              items={notifications}
              ariaLabel="Notifications"
              columns={notificationColumns}
              gridTemplateColumns="minmax(8rem, 0.8fr) minmax(20rem, 2.2fr) minmax(10rem, 0.9fr) minmax(11rem, 0.9fr)"
              estimateRowHeight={94}
              maxHeightClassName="max-h-[44rem]"
              overscan={10}
              rowKey={(notification) => notification.id}
              renderRow={(notification) => (
                <>
                  <div className="admin-table-cell">
                    <span
                      className={`pill ${
                        notification.is_read
                          ? 'border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          : 'border-sky-200 bg-sky-100 text-sky-700 dark:border-sky-900/70 dark:bg-sky-950/40 dark:text-sky-200'
                      }`}
                    >
                      {notification.is_read ? 'Read' : 'Unread'}
                    </span>
                  </div>
                  <div className="admin-table-cell">
                    <div className="flex items-start gap-3">
                      <div className="pt-0.5 text-base">{getNotificationIcon(notification.type)}</div>
                      <div className="min-w-0">
                        <p
                          className={`text-sm ${
                            notification.is_read
                              ? 'text-slate-800 dark:text-slate-200'
                              : 'font-semibold text-slate-900 dark:text-slate-100'
                          }`}
                        >
                          {notification.title}
                        </p>
                        {notification.message ? (
                          <p className="helper-copy mt-1 line-clamp-2">{notification.message}</p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  <div className="admin-table-cell body-copy whitespace-nowrap">
                    {formatTime(notification.created_at)}
                  </div>
                  <div className="admin-table-cell">
                    <div className="flex items-center justify-end gap-2">
                      {notification.link ? (
                        <button
                          type="button"
                          onClick={() => openNotificationLink(notification)}
                          className="admin-icon-action border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-800 dark:border-slate-700 dark:text-slate-300"
                          title="Open link"
                          aria-label={`Open notification link for ${notification.title}`}
                          disabled={anyActionPending}
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      ) : null}
                      {notification.is_read ? (
                        <button
                          type="button"
                          onClick={() => markUnreadMutation.mutate(notification.id)}
                          className="admin-icon-action border border-slate-200 text-amber-700 hover:bg-amber-50 hover:text-amber-800 dark:border-slate-700 dark:text-amber-300 dark:hover:bg-amber-950/30 dark:hover:text-amber-200"
                          title="Mark as unread"
                          aria-label={`Mark ${notification.title} as unread`}
                          disabled={anyActionPending}
                        >
                          <Mail className="w-4 h-4" />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => markReadMutation.mutate(notification.id)}
                          className="admin-icon-action border border-slate-200 text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800 dark:border-slate-700 dark:text-emerald-300 dark:hover:bg-emerald-950/30 dark:hover:text-emerald-200"
                          title="Mark as read"
                          aria-label={`Mark ${notification.title} as read`}
                          disabled={anyActionPending}
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          setConfirmAction({
                            title: 'Delete notification',
                            description: 'Are you sure you want to delete this notification?',
                            onConfirm: () => {
                              deleteMutation.mutate(notification.id)
                              setConfirmAction(null)
                            },
                          })
                        }}
                        className="admin-icon-action-danger border border-slate-200 text-rose-700 hover:bg-rose-50 hover:text-rose-800 dark:border-slate-700 dark:text-rose-300 dark:hover:bg-rose-950/30 dark:hover:text-rose-200"
                        title="Delete notification"
                        aria-label={`Delete notification ${notification.title}`}
                        disabled={anyActionPending}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </>
              )}
            />
            <div className="flex justify-center border-t border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-800 dark:bg-slate-950/70">
              {hasMore ? (
                <button
                  type="button"
                  onClick={() => setPage((previous) => previous + 1)}
                  className="btn-secondary"
                  disabled={isFetching || anyActionPending}
                >
                  {isFetching ? 'Loading...' : 'Load more'}
                </button>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Showing all notifications</p>
              )}
            </div>
          </>
        )}
      </div>

      <ConfirmationDialog
        open={!!confirmAction}
        title={confirmAction?.title ?? ''}
        description={confirmAction?.description}
        confirmLabel="Delete"
        onConfirm={() => confirmAction?.onConfirm()}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  )
}
