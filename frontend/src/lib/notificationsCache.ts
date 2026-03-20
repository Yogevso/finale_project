import type { NotificationListResponse } from '@/types'

export const NOTIFICATIONS_QUERY_KEY = ['notifications'] as const

export function setNotificationReadState(
  previous: NotificationListResponse | undefined,
  notificationId: number,
  isRead: boolean,
) {
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
}

export function removeNotification(
  previous: NotificationListResponse | undefined,
  notificationId: number,
) {
  if (!previous) return previous

  const removed = previous.items.find((item) => item.id === notificationId)
  if (!removed) return previous

  return {
    ...previous,
    items: previous.items.filter((item) => item.id !== notificationId),
    total: Math.max(0, previous.total - 1),
    unread_count: removed.is_read ? previous.unread_count : Math.max(0, previous.unread_count - 1),
  }
}

export function markAllNotificationsRead(previous: NotificationListResponse | undefined) {
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
}

export function deleteReadNotifications(previous: NotificationListResponse | undefined) {
  if (!previous) return previous

  const unreadItems = previous.items.filter((item) => !item.is_read)
  return {
    ...previous,
    items: unreadItems,
    total: unreadItems.length,
    unread_count: unreadItems.length,
  }
}
