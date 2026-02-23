import type { MessageResponse, NotificationCountResponse, NotificationListResponse } from '@/types'
import type { ApiHttpClient, Constructor } from './httpClient'

export const NotificationsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getNotifications(
      unreadOnly: boolean = false,
      limit: number = 50,
    ): Promise<NotificationListResponse> {
      const { data } = await this.client.get<NotificationListResponse>('/notifications', {
        params: { unread_only: unreadOnly, limit },
      })
      return data
    }

    async getNotificationCount(): Promise<NotificationCountResponse> {
      const { data } = await this.client.get<NotificationCountResponse>('/notifications/count')
      return data
    }

    async markNotificationRead(notificationId: number): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponse>(`/notifications/${notificationId}/read`)
      return data
    }

    async markNotificationUnread(notificationId: number): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponse>(`/notifications/${notificationId}/unread`)
      return data
    }

    async markAllNotificationsRead(notificationIds?: number[]): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponse>('/notifications/read', {
        notification_ids: notificationIds || null,
      })
      return data
    }

    async deleteNotification(notificationId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(`/notifications/${notificationId}`)
      return data
    }

    async deleteAllNotifications(readOnly: boolean = true): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>('/notifications', {
        params: { read_only: readOnly },
      })
      return data
    }
  }

