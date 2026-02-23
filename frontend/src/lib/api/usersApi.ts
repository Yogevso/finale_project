import type { User, UserRole } from '@/types'
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
      const { data } = await this.client.get<User[]>('/users', { params })
      return data
    }

    async getUser(id: number): Promise<User> {
      const { data } = await this.client.get<User>(`/users/${id}`)
      return data
    }

    async createUser(userData: {
      email: string
      username: string
      full_name: string
      password: string
      role: UserRole
      tenant_id?: number
    }): Promise<User> {
      const { data } = await this.client.post<User>('/users', userData)
      return data
    }

    async updateUser(id: number, userData: {
      email?: string
      full_name?: string
      role?: UserRole
      is_active?: boolean
      tenant_id?: number | null
    }): Promise<User> {
      const { data } = await this.client.put<User>(`/users/${id}`, userData)
      return data
    }

    async deleteUser(id: number): Promise<void> {
      await this.client.delete(`/users/${id}`)
    }
  }

