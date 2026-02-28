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
  type TokenResponseDto,
  type UserDto,
  mapMessageResponseDto,
  mapTokenResponseDto,
  mapUserDto,
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
      const { data } = await this.client.get<SystemSettingsResponse>('/system/settings')
      return data
    }

    async updateSystemSettings(payload: SystemSettingsUpdate): Promise<SystemSettingsResponse> {
      const { data } = await this.client.put<SystemSettingsResponse>('/system/settings', payload)
      return data
    }

    async getRbacPolicies(): Promise<RbacPoliciesResponse> {
      const { data } = await this.client.get<RbacPoliciesResponse>('/rbac/policies')
      return data
    }

    async updateRbacPolicies(payload: RbacPoliciesUpdate): Promise<RbacPoliciesResponse> {
      const { data } = await this.client.put<RbacPoliciesResponse>('/rbac/policies', payload)
      return data
    }
  }

