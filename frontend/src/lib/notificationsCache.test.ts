import { describe, expect, it } from 'vitest'

import {
  deleteReadNotifications,
  markAllNotificationsRead,
  removeNotification,
  setNotificationReadState,
} from './notificationsCache'
import type { NotificationListResponse } from '@/types'

function buildNotifications(): NotificationListResponse {
  return {
    items: [
      {
        id: 1,
        type: 'ticket_new_customer_msg',
        title: 'Unread support update',
        message: 'Customer replied',
        link: '/support?ticket=1',
        is_read: false,
        read_at: null,
        created_at: '2026-03-27T10:00:00Z',
      },
      {
        id: 2,
        type: 'review_submitted',
        title: 'Already read review',
        message: 'Review pending',
        link: '/reviews',
        is_read: true,
        read_at: '2026-03-27T09:00:00Z',
        created_at: '2026-03-27T08:00:00Z',
      },
    ],
    total: 2,
    unread_count: 1,
  }
}

describe('notificationsCache', () => {
  it('updates unread counters when a notification read state changes', () => {
    const markedRead = setNotificationReadState(buildNotifications(), 1, true)
    expect(markedRead?.unread_count).toBe(0)
    expect(markedRead?.items[0].is_read).toBe(true)
    expect(markedRead?.items[0].read_at).not.toBeNull()

    const markedUnread = setNotificationReadState(markedRead, 2, false)
    expect(markedUnread?.unread_count).toBe(1)
    expect(markedUnread?.items[1].is_read).toBe(false)
    expect(markedUnread?.items[1].read_at).toBeNull()
  })

  it('removes notifications without leaving stale totals or unread counts', () => {
    const afterUnreadRemoval = removeNotification(buildNotifications(), 1)
    expect(afterUnreadRemoval?.items).toHaveLength(1)
    expect(afterUnreadRemoval?.total).toBe(1)
    expect(afterUnreadRemoval?.unread_count).toBe(0)

    const afterReadRemoval = removeNotification(buildNotifications(), 2)
    expect(afterReadRemoval?.items).toHaveLength(1)
    expect(afterReadRemoval?.total).toBe(1)
    expect(afterReadRemoval?.unread_count).toBe(1)
  })

  it('marks all notifications as read without changing the item count', () => {
    const updated = markAllNotificationsRead(buildNotifications())

    expect(updated?.unread_count).toBe(0)
    expect(updated?.total).toBe(2)
    expect(updated?.items.every((item) => item.is_read)).toBe(true)
  })

  it('deletes only read notifications and keeps unread counts aligned', () => {
    const updated = deleteReadNotifications(buildNotifications())

    expect(updated?.items).toHaveLength(1)
    expect(updated?.items[0].id).toBe(1)
    expect(updated?.total).toBe(1)
    expect(updated?.unread_count).toBe(1)
  })
})
