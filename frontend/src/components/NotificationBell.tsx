import { useCallback, useEffect, useId, useRef, useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Bell,
  Check,
  CheckCheck,
  ClipboardCheck,
  FileText,
  MessageSquare,
  Trash2,
  X,
} from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { api } from '@/lib/api'
import {
  markAllNotificationsRead,
  NOTIFICATIONS_QUERY_KEY,
  removeNotification,
  setNotificationReadState,
} from '@/lib/notificationsCache'
import type { Notification, NotificationListResponse } from '@/types'

const BELL_NOTIFICATIONS_LIMIT = 20

export default function NotificationBell() {
  const panelId = useId()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const isNotificationsPage = location.pathname === '/notifications'

  const closeDropdown = useCallback((options?: { restoreFocus?: boolean }) => {
    setIsOpen(false)
    if (options?.restoreFocus) {
      requestAnimationFrame(() => {
        triggerRef.current?.focus()
      })
    }
  }, [])

  const {
    data,
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: NOTIFICATIONS_QUERY_KEY,
    queryFn: () => api.getNotifications(false, BELL_NOTIFICATIONS_LIMIT),
    enabled: !isNotificationsPage,
    refetchInterval: isNotificationsPage ? false : 30000,
  })

  const notifications = (data?.items || []).slice(0, BELL_NOTIFICATIONS_LIMIT)
  const unreadCount = data?.unread_count || 0

  useEffect(() => {
    if (isOpen && !isNotificationsPage) {
      void refetch()
    }
  }, [isOpen, isNotificationsPage, refetch])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        closeDropdown()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [closeDropdown, isOpen])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closeDropdown({ restoreFocus: true })
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [closeDropdown, isOpen])

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
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
    },
  })

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.is_read) {
      await markReadMutation.mutateAsync(notification.id)
    }

    if (!notification.link) {
      return
    }

    closeDropdown()
    const link = notification.link
    if (link.startsWith('http://') || link.startsWith('https://')) {
      window.open(link, '_blank', 'noopener,noreferrer')
      return
    }
    navigate(link)
  }

  const getNotificationIcon = (notification: Pick<Notification, 'type' | 'link'>) => {
    if (notification.type === 'system' && notification.link?.startsWith('/chat')) {
      return <MessageSquare className="w-4 h-4 text-indigo-500" />
    }

    switch (notification.type) {
      case 'comment_added':
      case 'comment_reply':
        return <MessageSquare className="w-4 h-4 text-blue-500" />
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
    return date.toLocaleDateString()
  }

  const isBusy = markReadMutation.isPending || markAllReadMutation.isPending || deleteMutation.isPending
  const showSpinner = isLoading || (!data && isFetching)

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Icon Button */}
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen((previous) => !previous)}
        className="relative rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-haspopup="dialog"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="motion-enter-scale absolute -top-0.5 -right-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-blue-600 px-1 text-xs font-bold text-white" aria-live="polite" role="status">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          id={panelId}
          className="dropdown-menu motion-enter-slide absolute right-0 z-50 mt-2 w-96 overflow-hidden p-0 dark:bg-slate-900"
          role="dialog"
          aria-label="Notifications panel"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/70">
            <h3 className="font-display font-semibold text-slate-900 dark:text-slate-100">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={() => markAllReadMutation.mutate()}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
                  disabled={isBusy}
                  aria-label="Mark all notifications as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all read
                </button>
              )}
              <button
                type="button"
                onClick={() => closeDropdown({ restoreFocus: true })}
                className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-200"
                aria-label="Close notifications panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto">
            {showSpinner ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              </div>
            ) : !data && !isLoading ? (
              <div className="p-3">
                <ErrorState
                  tone="warning"
                  size="compact"
                  title="Failed to load notifications"
                  message="Please try again."
                  onRetry={() => void refetch()}
                />
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-3">
                <EmptyState
                  tone="info"
                  size="compact"
                  title="No notifications yet"
                  description="Updates and alerts will appear here."
                  icon={<Bell className="h-5 w-5" aria-hidden="true" />}
                />
              </div>
            ) : (
              notifications.map((notification, index) => (
                <div
                  key={notification.id}
                  onClick={() => void handleNotificationClick(notification)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      void handleNotificationClick(notification)
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  style={{ '--enter-delay': `${Math.min(index, 7) * 35}ms` } as CSSProperties}
                  className={`motion-enter-fade flex cursor-pointer items-start gap-3 border-b border-slate-50 px-4 py-3 transition-colors dark:border-slate-800 ${
                    notification.is_read
                      ? 'bg-white hover:bg-slate-50 dark:bg-slate-900 dark:hover:bg-slate-800/80'
                      : 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/30 dark:hover:bg-blue-900/40'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getNotificationIcon(notification)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${notification.is_read ? 'text-slate-700 dark:text-slate-200' : 'font-medium text-slate-900 dark:text-slate-100'}`}>
                      {notification.title}
                    </p>
                    {notification.message && (
                      <p className="mt-0.5 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
                        {notification.message}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-slate-400 dark:text-slate-500" title={new Date(notification.created_at).toLocaleString()}>
                      {formatTime(notification.created_at)}
                    </p>
                  </div>
                  <div className="flex-shrink-0 flex gap-1">
                    {!notification.is_read && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          markReadMutation.mutate(notification.id)
                        }}
                        className="rounded-full p-1 text-slate-400 hover:bg-blue-50 hover:text-blue-600 dark:text-slate-500 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
                        title="Mark as read"
                        disabled={isBusy}
                        aria-label={`Mark notification "${notification.title}" as read`}
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteMutation.mutate(notification.id)
                      }}
                      className="rounded-full p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:text-slate-500 dark:hover:bg-rose-950/30 dark:hover:text-rose-300"
                      title="Delete"
                      disabled={isBusy}
                      aria-label={`Delete notification "${notification.title}"`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-100 bg-slate-50 px-4 py-2 dark:border-slate-800 dark:bg-slate-950/70">
            <button
              type="button"
              onClick={() => {
                closeDropdown()
                navigate('/notifications')
              }}
              className="w-full text-center text-xs text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
            >
              See all notifications
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
