import type { User, UserRole } from '@/types'
import {
  type UserCreateDto,
  type UserDto,
  type UserUpdateDto,
  mapUserDto,
  mapUsersDto,
  toUserCreateDto,
  toUserUpdateDto,
} from './dto'
import type { ApiHttpClient, Constructor } from './httpClient'

export const UsersApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

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

    async updateMyProfile(profile: { full_name: string }): Promise<User> {
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

    async deleteUser(id: number): Promise<void> {
      await this.client.delete(`/users/${id}`)
    }
  }

