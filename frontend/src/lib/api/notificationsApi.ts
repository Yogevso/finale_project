import type { MessageResponse, NotificationCountResponse, NotificationListResponse } from '@/types'
import {
  type MessageResponseDto,
  type NotificationCountResponseDto,
  type NotificationListResponseDto,
  mapMessageResponseDto,
  mapNotificationCountResponseDto,
  mapNotificationListResponseDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export const NotificationsApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    async getNotifications(
      unreadOnly: boolean = false,
      limit: number = 50,
    ): Promise<NotificationListResponse> {
      const { data } = await this.client.get<NotificationListResponseDto>('/notifications', {
        params: { unread_only: unreadOnly, limit },
      })
      return mapNotificationListResponseDto(data)
    }

    async getNotificationCount(): Promise<NotificationCountResponse> {
      const { data } = await this.client.get<NotificationCountResponseDto>('/notifications/count')
      return mapNotificationCountResponseDto(data)
    }

    async markNotificationRead(notificationId: number): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponseDto>(`/notifications/${notificationId}/read`)
      return mapMessageResponseDto(data)
    }

    async markNotificationUnread(notificationId: number): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponseDto>(
        `/notifications/${notificationId}/unread`,
      )
      return mapMessageResponseDto(data)
    }

    async markAllNotificationsRead(notificationIds?: number[]): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponseDto>('/notifications/read', {
        notification_ids: notificationIds || null,
      })
      return mapMessageResponseDto(data)
    }

    async deleteNotification(notificationId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(`/notifications/${notificationId}`)
      return mapMessageResponseDto(data)
    }

    async deleteAllNotifications(readOnly: boolean = true): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>('/notifications', {
        params: { read_only: readOnly },
      })
      return mapMessageResponseDto(data)
    }
  }

