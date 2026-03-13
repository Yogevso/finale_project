import { useEffect, useRef, useState } from 'react'
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

import { api } from '@/lib/api'
import type { Notification, NotificationListResponse, NotificationType } from '@/types'

const NOTIFICATIONS_QUERY_KEY = ['notifications'] as const
const BELL_NOTIFICATIONS_LIMIT = 20

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const isNotificationsPage = location.pathname === '/notifications'

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
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

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
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (notificationId: number) => api.deleteNotification(notificationId),
    onSuccess: (_, notificationId) => {
      removeNotificationFromCache(notificationId)
    },
  })

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.is_read) {
      await markReadMutation.mutateAsync(notification.id)
    }

    if (!notification.link) {
      return
    }

    setIsOpen(false)
    const link = notification.link
    if (link.startsWith('http://') || link.startsWith('https://')) {
      window.open(link, '_blank', 'noopener,noreferrer')
      return
    }
    navigate(link)
  }

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
        onClick={() => setIsOpen((previous) => !previous)}
        className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-xs font-bold text-white bg-sky-600 rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 surface-card overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50">
            <h3 className="font-semibold text-slate-900 font-display">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllReadMutation.mutate()}
                  className="text-xs text-sky-600 hover:text-sky-800 flex items-center gap-1"
                  disabled={isBusy}
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all read
                </button>
              )}
              <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto">
            {showSpinner ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-sky-600"></div>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-slate-500">
                <Bell className="w-8 h-8 mb-2 text-slate-300" />
                <p className="text-sm">No notifications yet</p>
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  onClick={() => void handleNotificationClick(notification)}
                  className={`flex items-start gap-3 px-4 py-3 border-b border-slate-50 cursor-pointer transition-colors ${
                    notification.is_read
                      ? 'bg-white hover:bg-slate-50'
                      : 'bg-sky-50 hover:bg-sky-100'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${notification.is_read ? 'text-slate-700' : 'text-slate-900 font-medium'}`}>
                      {notification.title}
                    </p>
                    {notification.message && (
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                        {notification.message}
                      </p>
                    )}
                    <p className="text-xs text-slate-400 mt-1">
                      {formatTime(notification.created_at)}
                    </p>
                  </div>
                  <div className="flex-shrink-0 flex gap-1">
                    {!notification.is_read && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          markReadMutation.mutate(notification.id)
                        }}
                        className="p-1 text-slate-400 hover:text-sky-600 hover:bg-sky-50 rounded-full"
                        title="Mark as read"
                        disabled={isBusy}
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteMutation.mutate(notification.id)
                      }}
                      className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-full"
                      title="Delete"
                      disabled={isBusy}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-slate-100 bg-slate-50">
            <button
              onClick={() => {
                setIsOpen(false)
                navigate('/notifications')
              }}
              className="text-xs text-sky-600 hover:text-sky-800 w-full text-center"
            >
              See all notifications
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
