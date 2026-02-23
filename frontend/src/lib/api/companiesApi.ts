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
      const { data } = await this.client.get<CompanyListResponse>('/companies', { params })
      return data
    }

    async getCompany(id: number): Promise<Company> {
      const { data } = await this.client.get<Company>(`/companies/${id}`)
      return data
    }

    async createCompany(company: CompanyCreate): Promise<Company> {
      const { data } = await this.client.post<Company>('/companies', company)
      return data
    }

    async updateCompany(id: number, company: CompanyUpdate): Promise<Company> {
      const { data } = await this.client.put<Company>(`/companies/${id}`, company)
      return data
    }

    async deleteCompany(id: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(`/companies/${id}`)
      return data
    }

    async getCompanyUsers(companyId: number): Promise<CompanyUser[]> {
      const { data } = await this.client.get<CompanyUser[]>(`/companies/${companyId}/users`)
      return data
    }

    async addUserToCompany(companyId: number, userData: CompanyUserAdd): Promise<MessageResponse> {
      const { data } = await this.client.post<MessageResponse>(`/companies/${companyId}/users`, userData)
      return data
    }

    async removeUserFromCompany(companyId: number, userId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(`/companies/${companyId}/users/${userId}`)
      return data
    }

    async getCompanyDocuments(
      companyId: number,
      params?: {
        page?: number
        per_page?: number
      },
    ): Promise<CompanyDocumentsResponse> {
      const { data } = await this.client.get<CompanyDocumentsResponse>(
        `/companies/${companyId}/documents`,
        { params },
      )
      return data
    }
  }

