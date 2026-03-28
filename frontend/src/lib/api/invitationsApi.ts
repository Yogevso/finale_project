import type {
  AcceptInvitationRequest,
  Invitation,
  InvitationCreate,
  InvitationEmailPreviewResponse,
  InvitationListResponse,
  InvitationStatus,
  InvitationValidateResponse,
  TokenResponse,
} from '@/types'
import {
  type AcceptInvitationRequestDto,
  type InvitationCreateDto,
  type InvitationDto,
  type InvitationEmailPreviewResponseDto,
  type InvitationListResponseDto,
  type InvitationValidateResponseDto,
  type TokenResponseDto,
  mapInvitationDto,
  mapInvitationEmailPreviewResponseDto,
  mapInvitationListResponseDto,
  mapInvitationValidateResponseDto,
  mapTokenResponseDto,
  toAcceptInvitationRequestDto,
  toInvitationCreateDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export const InvitationsApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
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

    async getInvitationEmailPreview(id: number): Promise<InvitationEmailPreviewResponse> {
      const { data } = await this.client.get<InvitationEmailPreviewResponseDto>(
        `/invitations/${id}/email-preview`,
      )
      return mapInvitationEmailPreviewResponseDto(data)
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

