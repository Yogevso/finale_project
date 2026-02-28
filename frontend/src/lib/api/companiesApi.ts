import type {
  Company,
  CompanyCreate,
  CompanyDocumentsResponse,
  CompanyListResponse,
  CompanyUpdate,
  CompanyUser,
  CompanyUserAdd,
  MessageResponse,
} from '@/types'
import {
  type CompanyCreateDto,
  type CompanyDocumentsResponseDto,
  type CompanyDto,
  type CompanyListResponseDto,
  type CompanyUpdateDto,
  type CompanyUserAddDto,
  type CompanyUserDto,
  type MessageResponseDto,
  mapCompanyDocumentsResponseDto,
  mapCompanyDto,
  mapCompanyListResponseDto,
  mapCompanyUsersDto,
  mapMessageResponseDto,
  toCompanyCreateDto,
  toCompanyUpdateDto,
  toCompanyUserAddDto,
} from './dto'
import type { ApiHttpClient, Constructor } from './httpClient'

export const CompaniesApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getCompanies(params?: {
      page?: number
      per_page?: number
      search?: string
      company_type?: string
      is_active?: boolean
    }): Promise<CompanyListResponse> {
      const { data } = await this.client.get<CompanyListResponseDto>('/companies', { params })
      return mapCompanyListResponseDto(data)
    }

    async getCompany(id: number): Promise<Company> {
      const { data } = await this.client.get<CompanyDto>(`/companies/${id}`)
      return mapCompanyDto(data)
    }

    async createCompany(company: CompanyCreate): Promise<Company> {
      const payload = toCompanyCreateDto(company)
      const { data } = await this.client.post<CompanyDto>('/companies', payload as CompanyCreateDto)
      return mapCompanyDto(data)
    }

    async updateCompany(id: number, company: CompanyUpdate): Promise<Company> {
      const payload = toCompanyUpdateDto(company)
      const { data } = await this.client.put<CompanyDto>(`/companies/${id}`, payload as CompanyUpdateDto)
      return mapCompanyDto(data)
    }

    async deleteCompany(id: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(`/companies/${id}`)
      return mapMessageResponseDto(data)
    }

    async getCompanyUsers(companyId: number): Promise<CompanyUser[]> {
      const { data } = await this.client.get<CompanyUserDto[]>(`/companies/${companyId}/users`)
      return mapCompanyUsersDto(data)
    }

    async addUserToCompany(companyId: number, userData: CompanyUserAdd): Promise<MessageResponse> {
      const payload = toCompanyUserAddDto(userData)
      const { data } = await this.client.post<MessageResponseDto>(
        `/companies/${companyId}/users`,
        payload as CompanyUserAddDto,
      )
      return mapMessageResponseDto(data)
    }

    async removeUserFromCompany(companyId: number, userId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(
        `/companies/${companyId}/users/${userId}`,
      )
      return mapMessageResponseDto(data)
    }

    async getCompanyDocuments(
      companyId: number,
      params?: {
        page?: number
        per_page?: number
        scope?: 'assigned' | 'owned' | 'customer_visible'
      },
    ): Promise<CompanyDocumentsResponse> {
      const { data } = await this.client.get<CompanyDocumentsResponseDto>(
        `/companies/${companyId}/documents`,
        { params },
      )
      return mapCompanyDocumentsResponseDto(data)
    }
  }

