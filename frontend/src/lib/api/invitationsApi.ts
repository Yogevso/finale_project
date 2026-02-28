import type {
  AcceptInvitationRequest,
  Invitation,
  InvitationCreate,
  InvitationListResponse,
  InvitationStatus,
  InvitationValidateResponse,
  TokenResponse,
} from '@/types'
import {
  type AcceptInvitationRequestDto,
  type InvitationCreateDto,
  type InvitationDto,
  type InvitationListResponseDto,
  type InvitationValidateResponseDto,
  type TokenResponseDto,
  mapInvitationDto,
  mapInvitationListResponseDto,
  mapInvitationValidateResponseDto,
  mapTokenResponseDto,
  toAcceptInvitationRequestDto,
  toInvitationCreateDto,
} from './dto'
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
      const { data } = await this.client.get<InvitationListResponseDto>('/invitations', { params })
      return mapInvitationListResponseDto(data)
    }

    async getInvitation(id: number): Promise<Invitation> {
      const { data } = await this.client.get<InvitationDto>(`/invitations/${id}`)
      return mapInvitationDto(data)
    }

    async createInvitation(invitation: InvitationCreate): Promise<Invitation> {
      const payload = toInvitationCreateDto(invitation)
      const { data } = await this.client.post<InvitationDto>(
        '/invitations',
        payload as InvitationCreateDto,
      )
      return mapInvitationDto(data)
    }

    async cancelInvitation(id: number): Promise<void> {
      await this.client.delete(`/invitations/${id}`)
    }

    async resendInvitation(id: number): Promise<Invitation> {
      const { data } = await this.client.post<InvitationDto>(`/invitations/${id}/resend`)
      return mapInvitationDto(data)
    }

    async validateInvitation(token: string): Promise<InvitationValidateResponse> {
      const { data } = await this.client.get<InvitationValidateResponseDto>(`/auth/invitation/${token}`)
      return mapInvitationValidateResponseDto(data)
    }

    async acceptInvitation(request: AcceptInvitationRequest): Promise<TokenResponse> {
      const payload = toAcceptInvitationRequestDto(request as AcceptInvitationRequestDto)
      const { data } = await this.client.post<TokenResponseDto>(
        '/auth/invitation/accept',
        payload as AcceptInvitationRequestDto,
      )
      return mapTokenResponseDto(data)
    }
  }

