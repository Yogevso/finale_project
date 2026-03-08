import type {
  LoginRequest,
  MessageResponse,
  PasswordChange,
  RbacPoliciesResponse,
  RbacPoliciesUpdate,
  SystemSettingsResponse,
  SystemSettingsUpdate,
  TokenResponse,
  User,
  UserCreate,
} from '@/types'
import {
  type MessageResponseDto,
  type RbacPoliciesResponseDto,
  type RbacPoliciesUpdateDto,
  type SystemSettingsResponseDto,
  type SystemSettingsUpdateDto,
  type TokenResponseDto,
  type UserDto,
  mapMessageResponseDto,
  mapRbacPoliciesResponseDto,
  mapSystemSettingsResponseDto,
  mapTokenResponseDto,
  mapUserDto,
  toRbacPoliciesUpdateDto,
  toSystemSettingsUpdateDto,
} from './dto'
import type { ApiHttpClient, Constructor } from './httpClient'

export const AuthApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async login(credentials: LoginRequest): Promise<TokenResponse> {
      const { data } = await this.client.post<TokenResponseDto>('/auth/login', credentials)
      const payload = mapTokenResponseDto(data)
      this.setToken(payload.access_token, payload.refresh_token)
      return payload
    }

    async forgotPassword(identifier: string): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponseDto>('/auth/forgot-password', {
        identifier,
      })
      return mapMessageResponseDto(data)
    }

    async resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponseDto>('/auth/reset-password', {
        token,
        new_password: newPassword,
      })
      return mapMessageResponseDto(data)
    }

    async register(userData: UserCreate): Promise<User> {
      const { data } = await this.client.post<UserDto>('/auth/register', userData)
      return mapUserDto(data)
    }

    async getCurrentUser(): Promise<User> {
      const { data } = await this.client.get<UserDto>('/auth/me')
      return mapUserDto(data)
    }

    async changePassword(passwords: PasswordChange): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponseDto>('/auth/change-password', passwords)
      return mapMessageResponseDto(data)
    }

    async logout(): Promise<void> {
      try {
        await this.client.post('/auth/logout')
      } catch {
        // Ignore logout errors
      }
      this.clearTokens()
    }

    async getSystemSettings(): Promise<SystemSettingsResponse> {
      const { data } = await this.client.get<SystemSettingsResponseDto>('/system/settings')
      return mapSystemSettingsResponseDto(data)
    }

    async updateSystemSettings(payload: SystemSettingsUpdate): Promise<SystemSettingsResponse> {
      const requestDto = toSystemSettingsUpdateDto(payload)
      const { data } = await this.client.put<SystemSettingsResponseDto>(
        '/system/settings',
        requestDto as SystemSettingsUpdateDto,
      )
      return mapSystemSettingsResponseDto(data)
    }

    async getRbacPolicies(): Promise<RbacPoliciesResponse> {
      const { data } = await this.client.get<RbacPoliciesResponseDto>('/rbac/policies')
      return mapRbacPoliciesResponseDto(data)
    }

    async updateRbacPolicies(payload: RbacPoliciesUpdate): Promise<RbacPoliciesResponse> {
      const requestDto = toRbacPoliciesUpdateDto(payload)
      const { data } = await this.client.put<RbacPoliciesResponseDto>(
        '/rbac/policies',
        requestDto as RbacPoliciesUpdateDto,
      )
      return mapRbacPoliciesResponseDto(data)
    }
  }

