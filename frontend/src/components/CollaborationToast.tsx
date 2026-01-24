/**
 * CollaborationToast Component
 *
 * Shows toast notifications for collaboration events
 * like users joining or leaving a document.
 */

import { useEffect, useRef, useState } from 'react'
import { LogIn, LogOut, Save, History, X } from 'lucide-react'
import { useCollaborationStore, CollaborationNotification } from '@/stores/collaborationStore'

interface CollaborationToastProviderProps {
  documentId: number
  enabled?: boolean
}

interface ToastItem {
  id: string
  notification: CollaborationNotification
}

export function useCollaborationToasts(documentId: number, enabled = true) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const notifications = useCollaborationStore((state) => state.notifications)
  const dismissNotification = useCollaborationStore((state) => state.dismissNotification)
  const lastProcessedRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!enabled) return

    // Find new notifications for this document that haven't been shown
    const newNotifications = notifications.filter(
      (n) =>
        n.documentId === documentId &&
        !lastProcessedRef.current.has(n.id) &&
        // Only show notifications from the last 5 seconds
        Date.now() - n.timestamp.getTime() < 5000
    )

    newNotifications.forEach((notification) => {
      lastProcessedRef.current.add(notification.id)

      // Add to local toast state
      setToasts((prev) => [...prev, { id: notification.id, notification }])

      // Auto-dismiss after 3 seconds
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== notification.id))
        dismissNotification(notification.id)
      }, 3000)
    })

    // Cleanup old processed IDs
    if (lastProcessedRef.current.size > 100) {
      const oldIds = Array.from(lastProcessedRef.current).slice(0, 50)
      oldIds.forEach((id) => lastProcessedRef.current.delete(id))
    }
  }, [notifications, documentId, enabled, dismissNotification])

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    dismissNotification(id)
  }

  return { toasts, dismissToast }
}

function CollaborationToastItem({
  notification,
  onDismiss,
}: {
  notification: CollaborationNotification
  onDismiss: () => void
}) {
  const iconMap = {
    join: LogIn,
    leave: LogOut,
    edit: Save,
    version: History,
  }

  const Icon = iconMap[notification.type] || LogIn

  const bgColorMap = {
    join: 'bg-green-50 border-green-200',
    leave: 'bg-gray-50 border-gray-200',
    edit: 'bg-blue-50 border-blue-200',
    version: 'bg-purple-50 border-purple-200',
  }

  const iconColorMap = {
    join: 'text-green-600',
    leave: 'text-gray-600',
    edit: 'text-blue-600',
    version: 'text-purple-600',
  }

  const titleMap = {
    join: 'User joined',
    leave: 'User left',
    edit: 'Document updated',
    version: 'New version',
  }

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border shadow-sm animate-in slide-in-from-right-5 ${bgColorMap[notification.type]}`}
    >
      <Icon className={`w-5 h-5 mt-0.5 ${iconColorMap[notification.type]}`} />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm text-gray-900">
          {titleMap[notification.type]}
        </p>
        <p className="text-sm text-gray-600 truncate">{notification.message}</p>
      </div>
      <button
        onClick={onDismiss}
        className="text-gray-400 hover:text-gray-600 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

// Provider component that renders toasts
export function CollaborationToastProvider({
  documentId,
  enabled = true,
}: CollaborationToastProviderProps) {
  const { toasts, dismissToast } = useCollaborationToasts(documentId, enabled)

  if (toasts.length === 0) {
    return null
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
      {toasts.map((toast) => (
        <CollaborationToastItem
          key={toast.id}
          notification={toast.notification}
          onDismiss={() => dismissToast(toast.id)}
        />
      ))}
    </div>
  )
}

export default CollaborationToastProvider
