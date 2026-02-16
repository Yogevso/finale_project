import { useState, useEffect, useRef } from 'react'
import { Bell, Check, CheckCheck, Trash2, X, MessageSquare, FileText, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import type { Notification, NotificationType } from '@/types'
import { useNavigate } from 'react-router-dom'

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  // Fetch notification count on mount and periodically
  useEffect(() => {
    fetchNotificationCount()
    const interval = setInterval(fetchNotificationCount, 30000) // Every 30 seconds
    return () => clearInterval(interval)
  }, [])

  // Fetch full notifications when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications()
    }
  }, [isOpen])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchNotificationCount = async () => {
    try {
      const { unread_count } = await api.getNotificationCount()
      setUnreadCount(unread_count)
    } catch (error) {
      console.error('Failed to fetch notification count:', error)
    }
  }

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const { items, unread_count } = await api.getNotifications(false, 20)
      setNotifications(items)
      setUnreadCount(unread_count)
    } catch (error) {
      console.error('Failed to fetch notifications:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsRead = async (notificationId: number, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await api.markNotificationRead(notificationId)
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      )
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      await api.markAllNotificationsRead()
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  }

  const handleDelete = async (notificationId: number, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await api.deleteNotification(notificationId)
      const notification = notifications.find(n => n.id === notificationId)
      setNotifications(prev => prev.filter(n => n.id !== notificationId))
      if (notification && !notification.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1))
      }
    } catch (error) {
      console.error('Failed to delete notification:', error)
    }
  }

  const handleNotificationClick = async (notification: Notification) => {
    // Mark as read
    if (!notification.is_read) {
      await api.markNotificationRead(notification.id)
      setNotifications(prev => 
        prev.map(n => n.id === notification.id ? { ...n, is_read: true } : n)
      )
      setUnreadCount(prev => Math.max(0, prev - 1))
    }

    // Navigate to link if present
    if (notification.link) {
      setIsOpen(false)
      navigate(notification.link)
    }
  }

  const getNotificationIcon = (type: NotificationType) => {
    switch (type) {
      case 'COMMENT_ADDED':
      case 'COMMENT_REPLY':
        return <MessageSquare className="w-4 h-4 text-sky-500" />
      case 'DOCUMENT_CREATED':
      case 'DOCUMENT_UPDATED':
      case 'DOCUMENT_PUBLISHED':
      case 'VERSION_PUBLISHED':
        return <FileText className="w-4 h-4 text-emerald-500" />
      case 'SYSTEM':
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

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Icon Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
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
                  onClick={handleMarkAllAsRead}
                  className="text-xs text-sky-600 hover:text-sky-800 flex items-center gap-1"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all read
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto">
            {loading ? (
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
                  onClick={() => handleNotificationClick(notification)}
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
                        onClick={(e) => handleMarkAsRead(notification.id, e)}
                        className="p-1 text-slate-400 hover:text-sky-600 hover:bg-sky-50 rounded-full"
                        title="Mark as read"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={(e) => handleDelete(notification.id, e)}
                      className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-full"
                      title="Delete"
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
