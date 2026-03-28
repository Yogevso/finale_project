/**
 * Chat API mixin — internal messaging endpoints (Wave X.1)
 */

import type {
  Chat,
  ChatDetail,
  ChatEligibleUser,
  ChatListResponse,
  ChatMessage,
  ChatMessageListResponse,
  ChatParticipant,
  CreateDirectChatRequest,
  CreateGroupChatRequest,
  SendMessageRequest,
  AddParticipantRequest,
  UpdateChatRequest,
  UpdateParticipantRoleRequest,
} from '@/types/chat'
import type { ApiClientBase, Constructor } from './httpClient'

export const ChatApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    async getChatEligibleUsers(params?: { search?: string }): Promise<ChatEligibleUser[]> {
      const { data } = await this.client.get<ChatEligibleUser[]>('/chats/eligible-users', { params })
      return data
    }

    async getChats(): Promise<ChatListResponse> {
      const { data } = await this.client.get<ChatListResponse>('/chats')
      return data
    }

    async getPortalChats(): Promise<ChatListResponse> {
      const { data } = await this.client.get<ChatListResponse>('/portal/chats')
      return data
    }

    async createDirectChat(request: CreateDirectChatRequest): Promise<Chat> {
      const { data } = await this.client.post<Chat>('/chats/direct', request)
      return data
    }

    async createGroupChat(request: CreateGroupChatRequest): Promise<Chat> {
      const { data } = await this.client.post<Chat>('/chats/group', request)
      return data
    }

    async getChatDetail(chatId: number): Promise<ChatDetail> {
      const { data } = await this.client.get<ChatDetail>(`/chats/${chatId}`)
      return data
    }

    async getPortalChatDetail(chatId: number): Promise<ChatDetail> {
      const { data } = await this.client.get<ChatDetail>(`/portal/chats/${chatId}`)
      return data
    }

    async deleteChat(chatId: number): Promise<void> {
      await this.client.delete(`/chats/${chatId}`)
    }

    async getChatMessages(chatId: number, beforeId?: number, limit = 50): Promise<ChatMessageListResponse> {
      const { data } = await this.client.get<ChatMessageListResponse>(`/chats/${chatId}/messages`, {
        params: { before_id: beforeId, limit },
      })
      return data
    }

    async getPortalChatMessages(chatId: number, beforeId?: number, limit = 50): Promise<ChatMessageListResponse> {
      const { data } = await this.client.get<ChatMessageListResponse>(`/portal/chats/${chatId}/messages`, {
        params: { before_id: beforeId, limit },
      })
      return data
    }

    async sendChatMessage(chatId: number, request: SendMessageRequest): Promise<ChatMessage> {
      const { data } = await this.client.post<ChatMessage>(`/chats/${chatId}/messages`, request)
      return data
    }

    async sendPortalChatMessage(chatId: number, request: SendMessageRequest): Promise<ChatMessage> {
      const { data } = await this.client.post<ChatMessage>(`/portal/chats/${chatId}/messages`, request)
      return data
    }

    async uploadChatFile(chatId: number, file: File): Promise<ChatMessage> {
      const form = new FormData()
      form.append('file', file)
      const { data } = await this.client.post<ChatMessage>(`/chats/${chatId}/messages/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    }

    async addChatParticipant(chatId: number, request: AddParticipantRequest): Promise<ChatParticipant> {
      const { data } = await this.client.post<ChatParticipant>(`/chats/${chatId}/participants`, request)
      return data
    }

    async removeChatParticipant(chatId: number, userId: number): Promise<void> {
      await this.client.delete(`/chats/${chatId}/participants/${userId}`)
    }

    async markChatAsRead(chatId: number): Promise<void> {
      await this.client.post(`/chats/${chatId}/read`)
    }

    async markPortalChatAsRead(chatId: number): Promise<void> {
      await this.client.post(`/portal/chats/${chatId}/read`)
    }

    async searchChatMessages(chatId: number, q: string, limit = 50): Promise<ChatMessageListResponse> {
      const { data } = await this.client.get<ChatMessageListResponse>(`/chats/${chatId}/messages/search`, {
        params: { q, limit },
      })
      return data
    }

    async searchAllChatMessages(q: string, limit = 50): Promise<ChatMessageListResponse> {
      const { data } = await this.client.get<ChatMessageListResponse>('/chats/messages/search', {
        params: { q, limit },
      })
      return data
    }

    async updateChat(chatId: number, request: UpdateChatRequest): Promise<Chat> {
      const { data } = await this.client.patch<Chat>(`/chats/${chatId}`, request)
      return data
    }

    async toggleChatMute(chatId: number): Promise<{ is_muted: boolean }> {
      const { data } = await this.client.put<{ is_muted: boolean }>(`/chats/${chatId}/mute`)
      return data
    }

    async updateParticipantRole(
      chatId: number, userId: number, request: UpdateParticipantRoleRequest
    ): Promise<ChatParticipant> {
      const { data } = await this.client.patch<ChatParticipant>(
        `/chats/${chatId}/participants/${userId}/role`, request
      )
      return data
    }
  }
