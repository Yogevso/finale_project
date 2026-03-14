/**
 * Support ticket API mixin — customer support endpoints (Wave X.1)
 */

import type {
  SupportTicket,
  SupportTicketDetail,
  SupportTicketListResponse,
  SupportTicketCreate,
  SupportTicketUpdate,
  SupportTicketMessage,
  SupportTicketAssignment,
  SendTicketMessageRequest,
  AssignAgentRequest,
  SupportTicketStatus,
  CannedResponse,
  CannedResponseListResponse,
  CannedResponseCreate,
  CannedResponseUpdate,
} from '@/types/chat'
import type { ApiHttpClient, Constructor } from './httpClient'

export const SupportApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    // ---- Management endpoints (agents/admins) ----

    async getSupportTickets(params?: {
      status?: SupportTicketStatus
      page?: number
      page_size?: number
    }): Promise<SupportTicketListResponse> {
      const { data } = await this.client.get<SupportTicketListResponse>('/support/tickets', { params })
      return data
    }

    async getSupportTicket(ticketId: number): Promise<SupportTicketDetail> {
      const { data } = await this.client.get<SupportTicketDetail>(`/support/tickets/${ticketId}`)
      return data
    }

    async createSupportTicket(request: SupportTicketCreate): Promise<SupportTicket> {
      const { data } = await this.client.post<SupportTicket>('/support/tickets', request)
      return data
    }

    async updateSupportTicket(ticketId: number, request: SupportTicketUpdate): Promise<SupportTicket> {
      const { data } = await this.client.patch<SupportTicket>(`/support/tickets/${ticketId}`, request)
      return data
    }

    async getSupportTicketMessages(ticketId: number): Promise<SupportTicketMessage[]> {
      const { data } = await this.client.get<SupportTicketMessage[]>(`/support/tickets/${ticketId}/messages`)
      return data
    }

    async sendSupportTicketMessage(ticketId: number, request: SendTicketMessageRequest): Promise<SupportTicketMessage> {
      const { data } = await this.client.post<SupportTicketMessage>(`/support/tickets/${ticketId}/messages`, request)
      return data
    }

    async assignSupportAgent(ticketId: number, request: AssignAgentRequest): Promise<SupportTicketAssignment> {
      const { data } = await this.client.post<SupportTicketAssignment>(`/support/tickets/${ticketId}/assign`, request)
      return data
    }

    async unassignSupportAgent(ticketId: number, agentId: number): Promise<void> {
      await this.client.delete(`/support/tickets/${ticketId}/assign/${agentId}`)
    }

    async handoffTicket(ticketId: number, targetAgentId: number, note = ''): Promise<SupportTicketAssignment> {
      const { data } = await this.client.post<SupportTicketAssignment>(
        `/support/tickets/${ticketId}/handoff`,
        { target_agent_id: targetAgentId, note },
      )
      return data
    }

    async getTicketViewers(ticketId: number): Promise<{ ticket_id: number; viewer_ids: number[] }> {
      const { data } = await this.client.get<{ ticket_id: number; viewer_ids: number[] }>(
        `/support/tickets/${ticketId}/viewers`,
      )
      return data
    }

    // ---- Portal endpoints (customers) ----

    async getMyTickets(params?: {
      status?: SupportTicketStatus
      page?: number
      page_size?: number
    }): Promise<SupportTicketListResponse> {
      const { data } = await this.client.get<SupportTicketListResponse>('/portal/support/tickets', { params })
      return data
    }

    async getMyTicket(ticketId: number): Promise<SupportTicketDetail> {
      const { data } = await this.client.get<SupportTicketDetail>(`/portal/support/tickets/${ticketId}`)
      return data
    }

    async createMyTicket(request: SupportTicketCreate): Promise<SupportTicket> {
      const { data } = await this.client.post<SupportTicket>('/portal/support/tickets', request)
      return data
    }

    async sendMyTicketMessage(ticketId: number, request: SendTicketMessageRequest): Promise<SupportTicketMessage> {
      const { data } = await this.client.post<SupportTicketMessage>(`/portal/support/tickets/${ticketId}/messages`, request)
      return data
    }

    async closeMyTicket(ticketId: number): Promise<void> {
      await this.client.post(`/portal/support/tickets/${ticketId}/close`)
    }

    // ---- Canned responses (X1-103) ----

    async getCannedResponses(params?: {
      category?: string
      search?: string
    }): Promise<CannedResponseListResponse> {
      const { data } = await this.client.get<CannedResponseListResponse>('/support/canned-responses', { params })
      return data
    }

    async createCannedResponse(request: CannedResponseCreate): Promise<CannedResponse> {
      const { data } = await this.client.post<CannedResponse>('/support/canned-responses', request)
      return data
    }

    async updateCannedResponse(id: number, request: CannedResponseUpdate): Promise<CannedResponse> {
      const { data } = await this.client.patch<CannedResponse>(`/support/canned-responses/${id}`, request)
      return data
    }

    async deleteCannedResponse(id: number): Promise<void> {
      await this.client.delete(`/support/canned-responses/${id}`)
    }
  }
