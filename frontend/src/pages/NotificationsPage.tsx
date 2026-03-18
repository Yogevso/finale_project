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

import PageHeader from '@/components/PageHeader'
import ConfirmationDialog from '@/components/ConfirmationDialog'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import { useToast } from '@/lib/toast'
import type { Notification, NotificationListResponse, NotificationType } from '@/types'

const NOTIFICATIONS_QUERY_KEY = ['notifications'] as const
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

  const setReadStatusInCache = (notificationId: number, isRead: boolean) => {
    queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (previous) => {
      if (!previous) return previous

      let unreadDelta = 0
      const items = previous.items.map((item) => {
        if (item.id !== notificationId) return item
        if (item.is_read === isRead) return item
        unreadDelta = isRead ? -1 : 1
        return {
          ...item,
          is_read: isRead,
          read_at: isRead ? new Date().toISOString() : null,
        }
      })

      return {
        ...previous,
        items,
        unread_count: Math.max(0, previous.unread_count + unreadDelta),
      }
    })
  }

  const removeNotificationFromCache = (notificationId: number) => {
    queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (previous) => {
      if (!previous) return previous
      const removed = previous.items.find((item) => item.id === notificationId)
      if (!removed) return previous

      return {
        ...previous,
        items: previous.items.filter((item) => item.id !== notificationId),
        total: Math.max(0, previous.total - 1),
        unread_count: removed.is_read ? previous.unread_count : Math.max(0, previous.unread_count - 1),
      }
    })
  }

  const markReadMutation = useMutation({
    mutationFn: (notificationId: number) => api.markNotificationRead(notificationId),
    onSuccess: (_, notificationId) => {
      setReadStatusInCache(notificationId, true)
    },
  })

  const markUnreadMutation = useMutation({
    mutationFn: (notificationId: number) => api.markNotificationUnread(notificationId),
    onSuccess: (_, notificationId) => {
      setReadStatusInCache(notificationId, false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (notificationId: number) => api.deleteNotification(notificationId),
    onSuccess: (_, notificationId) => {
      removeNotificationFromCache(notificationId)
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => api.markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (previous) => {
        if (!previous) return previous
        const nowIso = new Date().toISOString()
        return {
          ...previous,
          unread_count: 0,
          items: previous.items.map((item) => ({
            ...item,
            is_read: true,
            read_at: item.read_at || nowIso,
          })),
        }
      })
      toast.success('All notifications marked as read')
    },
  })

  const deleteReadMutation = useMutation({
    mutationFn: () => api.deleteAllNotifications(true),
    onSuccess: () => {
      queryClient.setQueryData<NotificationListResponse>(NOTIFICATIONS_QUERY_KEY, (previous) => {
        if (!previous) return previous
        const unreadItems = previous.items.filter((item) => !item.is_read)
        return {
          ...previous,
          items: unreadItems,
          total: unreadItems.length,
          unread_count: unreadItems.length,
        }
      })
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        subtitle="Review updates and manage read status."
        meta={
          <span className="pill bg-sky-100 text-sky-800 border-sky-200">
            {unreadCount} unread
          </span>
        }
        actions={
          <>
            <button onClick={() => refetch()} className="btn-ghost inline-flex items-center gap-2" disabled={isFetching}>
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllReadMutation.mutate()}
                className="btn-secondary inline-flex items-center gap-2"
                disabled={anyActionPending}
              >
                <CheckCheck className="w-4 h-4" />
                Mark all read
              </button>
            )}
            {hasReadNotifications && (
              <button
                onClick={() => {
                  setConfirmAction({
                    title: 'Delete read notifications',
                    description: 'Are you sure you want to delete all read notifications? This cannot be undone.',
                    onConfirm: () => { deleteReadMutation.mutate(); setConfirmAction(null) },
                  })
                }}
                className="btn-ghost inline-flex items-center gap-2 text-rose-600 hover:text-rose-700"
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
          <div className="p-10 text-center text-slate-500">Loading notifications...</div>
        ) : isError ? (
          <div className="p-10 text-center">
            <p className="text-rose-600 mb-3">Failed to load notifications.</p>
            <button onClick={() => refetch()} className="btn-primary">
              Try again
            </button>
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Bell className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p className="text-sm">No notifications yet</p>
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Status</th>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Notification</th>
                  <th className="text-left text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Received</th>
                  <th className="text-right text-xs uppercase tracking-wider text-slate-500 px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {notifications.map((notification) => (
                  <tr
                    key={notification.id}
                    className={`border-b border-slate-100 hover:bg-slate-50 ${
                      notification.is_read ? 'bg-white' : 'bg-sky-50/60'
                    }`}
                  >
                    <td className="px-4 py-4 align-top">
                      <span
                        className={`pill ${
                          notification.is_read
                            ? 'bg-slate-100 text-slate-700 border-slate-200'
                            : 'bg-sky-100 text-sky-700 border-sky-200'
                        }`}
                      >
                        {notification.is_read ? 'Read' : 'Unread'}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-start gap-3">
                        <div className="pt-0.5 text-base">{getNotificationIcon(notification.type)}</div>
                        <div className="min-w-0">
                          <p
                            className={`text-sm ${
                              notification.is_read ? 'text-slate-800' : 'text-slate-900 font-semibold'
                            }`}
                          >
                            {notification.title}
                          </p>
                          {notification.message && (
                            <p className="text-xs text-slate-500 mt-1 line-clamp-2">{notification.message}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 align-top text-sm text-slate-600 whitespace-nowrap">
                      {formatTime(notification.created_at)}
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="flex items-center justify-end gap-2">
                        {notification.link && (
                          <button
                            onClick={() => openNotificationLink(notification)}
                            className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100"
                            title="Open link"
                            disabled={anyActionPending}
                          >
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        )}
                        {notification.is_read ? (
                          <button
                            onClick={() => markUnreadMutation.mutate(notification.id)}
                            className="p-2 rounded-lg border border-slate-200 text-amber-700 hover:bg-amber-50"
                            title="Mark as unread"
                            disabled={anyActionPending}
                          >
                            <Mail className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => markReadMutation.mutate(notification.id)}
                            className="p-2 rounded-lg border border-slate-200 text-emerald-700 hover:bg-emerald-50"
                            title="Mark as read"
                            disabled={anyActionPending}
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setConfirmAction({
                              title: 'Delete notification',
                              description: 'Are you sure you want to delete this notification?',
                              onConfirm: () => { deleteMutation.mutate(notification.id); setConfirmAction(null) },
                            })
                          }}
                          className="p-2 rounded-lg border border-slate-200 text-rose-700 hover:bg-rose-50"
                          title="Delete notification"
                          disabled={anyActionPending}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 py-4 border-t border-slate-200 bg-slate-50 flex justify-center">
              {hasMore ? (
                <button
                  onClick={() => setPage((previous) => previous + 1)}
                  className="btn-secondary"
                  disabled={isFetching || anyActionPending}
                >
                  {isFetching ? 'Loading...' : 'Load more'}
                </button>
              ) : (
                <p className="text-sm text-slate-500">Showing all notifications</p>
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
