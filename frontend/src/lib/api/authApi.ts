import type {
  LoginRequest,
  MessageResponse,
  PasswordChange,
  PublicRegistrationData,
  RbacPoliciesResponse,
  RbacPoliciesUpdate,
  SystemDocumentLifecycleSettingsResponse,
  SystemDocumentLifecycleSettingsUpdate,
  SystemEmailSettingsResponse,
  SystemEmailSettingsUpdate,
  SystemSettingsResponse,
  SystemSettingsUpdate,
  TokenResponse,
  User,
} from '@/types'
import {
  type MessageResponseDto,
  type RbacPoliciesResponseDto,
  type RbacPoliciesUpdateDto,
  type SystemDocumentLifecycleSettingsResponseDto,
  type SystemDocumentLifecycleSettingsUpdateDto,
  type SystemEmailSettingsResponseDto,
  type SystemEmailSettingsUpdateDto,
  type SystemSettingsResponseDto,
  type SystemSettingsUpdateDto,
  type TokenResponseDto,
  type UserDto,
  mapMessageResponseDto,
  mapSystemDocumentLifecycleSettingsResponseDto,
  mapSystemEmailSettingsResponseDto,
  mapRbacPoliciesResponseDto,
  mapSystemSettingsResponseDto,
  mapTokenResponseDto,
  mapUserDto,
  toSystemDocumentLifecycleSettingsUpdateDto,
  toSystemEmailSettingsUpdateDto,
  toRbacPoliciesUpdateDto,
  toSystemSettingsUpdateDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export const AuthApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
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

    async register(userData: PublicRegistrationData): Promise<User> {
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

    async getSystemDocumentLifecycleSettings(): Promise<SystemDocumentLifecycleSettingsResponse> {
      const { data } = await this.client.get<SystemDocumentLifecycleSettingsResponseDto>(
        '/system/settings/document-lifecycle',
      )
      return mapSystemDocumentLifecycleSettingsResponseDto(data)
    }

    async updateSystemDocumentLifecycleSettings(
      payload: SystemDocumentLifecycleSettingsUpdate,
    ): Promise<SystemDocumentLifecycleSettingsResponse> {
      const requestDto = toSystemDocumentLifecycleSettingsUpdateDto(payload)
      const { data } = await this.client.put<SystemDocumentLifecycleSettingsResponseDto>(
        '/system/settings/document-lifecycle',
        requestDto as SystemDocumentLifecycleSettingsUpdateDto,
      )
      return mapSystemDocumentLifecycleSettingsResponseDto(data)
    }

    async getSystemEmailSettings(): Promise<SystemEmailSettingsResponse> {
      const { data } = await this.client.get<SystemEmailSettingsResponseDto>(
        '/system/settings/email',
      )
      return mapSystemEmailSettingsResponseDto(data)
    }

    async updateSystemEmailSettings(
      payload: SystemEmailSettingsUpdate,
    ): Promise<SystemEmailSettingsResponse> {
      const requestDto = toSystemEmailSettingsUpdateDto(payload)
      const { data } = await this.client.put<SystemEmailSettingsResponseDto>(
        '/system/settings/email',
        requestDto as SystemEmailSettingsUpdateDto,
      )
      return mapSystemEmailSettingsResponseDto(data)
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
