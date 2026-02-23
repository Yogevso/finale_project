import type {
  AcceptInvitationRequest,
  Invitation,
  InvitationCreate,
  InvitationListResponse,
  InvitationStatus,
  InvitationValidateResponse,
  TokenResponse,
} from '@/types'
import type { ApiHttpClient, Constructor } from './httpClient'

export const InvitationsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getInvitations(params?: {
      page?: number
      per_page?: number
      status?: InvitationStatus
    }): Promise<InvitationListResponse> {
      const { data } = await this.client.get<InvitationListResponse>('/invitations', { params })
      return data
    }

    async getInvitation(id: number): Promise<Invitation> {
      const { data } = await this.client.get<Invitation>(`/invitations/${id}`)
      return data
    }

    async createInvitation(invitation: InvitationCreate): Promise<Invitation> {
      const { data } = await this.client.post<Invitation>('/invitations', invitation)
      return data
    }

    async cancelInvitation(id: number): Promise<void> {
      await this.client.delete(`/invitations/${id}`)
    }

    async resendInvitation(id: number): Promise<Invitation> {
      const { data } = await this.client.post<Invitation>(`/invitations/${id}/resend`)
      return data
    }

    async validateInvitation(token: string): Promise<InvitationValidateResponse> {
      const { data } = await this.client.get<InvitationValidateResponse>(`/auth/invitation/${token}`)
      return data
    }

    async acceptInvitation(request: AcceptInvitationRequest): Promise<TokenResponse> {
      const { data } = await this.client.post<TokenResponse>('/auth/invitation/accept', request)
      return data
    }
  }

