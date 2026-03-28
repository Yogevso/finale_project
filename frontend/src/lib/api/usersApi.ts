import type {
  SecurityEventListResponse,
  SessionBulkRevokeResponse,
  User,
  UserOnboardingState,
  UserOnboardingStateUpdate,
  UserRole,
  UserSessionListResponse,
} from '@/types'
import {
  type UserCreateDto,
  type UserDto,
  type UserUpdateDto,
  mapUserDto,
  mapUsersDto,
  toUserCreateDto,
  toUserUpdateDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export const UsersApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    async getUsers(params?: {
      role?: UserRole
      company_id?: number
      is_active?: boolean
      search?: string
    }): Promise<User[]> {
      const { data } = await this.client.get<UserDto[]>('/users', { params })
      return mapUsersDto(data)
    }

    async getUser(id: number): Promise<User> {
      const { data } = await this.client.get<UserDto>(`/users/${id}`)
      return mapUserDto(data)
    }

    async createUser(userData: {
      email: string
      username: string
      full_name: string
      password: string
      role: UserRole
      tenant_id?: number
    }): Promise<User> {
      const payload = toUserCreateDto(userData)
      const { data } = await this.client.post<UserDto>('/users', payload as UserCreateDto)
      return mapUserDto(data)
    }

    async updateUser(id: number, userData: {
      email?: string
      full_name?: string
      role?: UserRole
      is_active?: boolean
      tenant_id?: number | null
    }): Promise<User> {
      const payload = toUserUpdateDto(userData)
      const { data } = await this.client.put<UserDto>(`/users/${id}`, payload as UserUpdateDto)
      return mapUserDto(data)
    }

    async updateMyProfile(profile: {
      full_name?: string
      timezone?: string
      locale?: string
    }): Promise<User> {
      const { data } = await this.client.patch<UserDto>('/users/me', profile)
      return mapUserDto(data)
    }

    async updateMyNotificationPreferences(
      notificationPreferences: Record<string, boolean>,
    ): Promise<Record<string, boolean>> {
      const { data } = await this.client.patch<{ notification_preferences: Record<string, boolean> }>(
        '/users/me/notification-preferences',
        { notification_preferences: notificationPreferences },
      )
      return data.notification_preferences
    }

    async getMyOnboardingState(): Promise<UserOnboardingState> {
      const { data } = await this.client.get<UserOnboardingState>('/users/me/onboarding')
      return data
    }

    async updateMyOnboardingState(
      payload: UserOnboardingStateUpdate,
    ): Promise<UserOnboardingState> {
      const { data } = await this.client.patch<UserOnboardingState>(
        '/users/me/onboarding',
        payload,
      )
      return data
    }

    async uploadMyAvatar(file: File): Promise<{ avatar_url: string; message: string }> {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await this.client.post<{ avatar_url: string; message: string }>(
        '/users/me/avatar',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      return data
    }

    async getMySessions(): Promise<UserSessionListResponse> {
      const { data } = await this.client.get<UserSessionListResponse>('/users/me/sessions')
      return data
    }

    async revokeMySession(sessionId: number): Promise<{ message: string }> {
      const { data } = await this.client.delete<{ message: string }>(`/users/me/sessions/${sessionId}`)
      return data
    }

    async revokeAllMyOtherSessions(): Promise<SessionBulkRevokeResponse> {
      const { data } = await this.client.delete<SessionBulkRevokeResponse>('/users/me/sessions')
      return data
    }

    async getMySecurityEvents(params?: {
      page?: number
      page_size?: number
    }): Promise<SecurityEventListResponse> {
      const { data } = await this.client.get<SecurityEventListResponse>('/users/me/security-events', {
        params,
      })
      return data
    }

    async deleteUser(id: number): Promise<void> {
      await this.client.delete(`/users/${id}`)
    }

    async hardDeleteUser(id: number): Promise<void> {
      await this.client.delete(`/users/${id}/hard-delete`)
    }
  }

