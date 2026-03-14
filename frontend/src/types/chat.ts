/**
 * Chat & Support types (Wave X.1)
 */

// ---- Chat types ----

export type ChatType = 'direct' | 'group'
export type ChatParticipantRole = 'owner' | 'admin' | 'member'
export type ChatMessageType = 'text' | 'system' | 'file'

export interface ChatParticipant {
  id: number
  user_id: number
  role: ChatParticipantRole
  joined_at: string
  last_read_at: string | null
  is_muted: boolean
  user_full_name: string | null
}

export interface ChatMessage {
  id: number
  chat_id: number
  sender_id: number
  content: string
  message_type: ChatMessageType
  file_url: string | null
  file_name: string | null
  file_size: number | null
  file_mime_type: string | null
  created_at: string
  updated_at: string
  sender_full_name: string | null
}

export interface Chat {
  id: number
  type: ChatType
  name: string | null
  created_by: number
  tenant_id: number
  last_message_at: string | null
  created_at: string
  updated_at: string
}

export interface ChatDetail extends Chat {
  participants: ChatParticipant[]
}

export interface ChatListItem {
  chat: Chat
  display_name: string
  last_message: ChatMessage | null
  unread_count: number
  is_muted: boolean
}

export interface ChatListResponse {
  items: ChatListItem[]
  total: number
}

export interface ChatMessageListResponse {
  items: ChatMessage[]
  has_more: boolean
}

export interface CreateDirectChatRequest {
  user_id: number
}

export interface CreateGroupChatRequest {
  name: string
  participant_ids: number[]
}

export interface SendMessageRequest {
  content: string
}

export interface AddParticipantRequest {
  user_id: number
}

export interface UpdateChatRequest {
  name?: string
}

export interface UpdateParticipantRoleRequest {
  role: ChatParticipantRole
}

// ---- Support types ----

export type SupportTicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'
export type SupportTicketPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface SupportTicket {
  id: number
  customer_id: number
  subject: string
  status: SupportTicketStatus
  priority: SupportTicketPriority
  category: string | null
  feedback_id: number | null
  tenant_id: number
  created_at: string
  updated_at: string
  resolved_at: string | null
  customer_full_name: string | null
}

export interface SupportTicketMessage {
  id: number
  ticket_id: number
  sender_id: number
  sender_type: 'customer' | 'agent'
  content: string
  is_internal_note: boolean
  created_at: string
  sender_full_name: string | null
}

export interface SupportTicketAssignment {
  id: number
  ticket_id: number
  agent_id: number
  is_primary: boolean
  assigned_at: string
  agent_full_name: string | null
}

export interface SupportTicketDetail extends SupportTicket {
  messages: SupportTicketMessage[]
  assignments: SupportTicketAssignment[]
}

export interface SupportTicketListResponse {
  items: SupportTicket[]
  total: number
  page: number
  page_size: number
}

export interface SupportTicketCreate {
  subject: string
  content: string
  priority?: SupportTicketPriority
  category?: string
  feedback_id?: number
}

export interface SupportTicketUpdate {
  subject?: string
  status?: SupportTicketStatus
  priority?: SupportTicketPriority
  category?: string
}

export interface SendTicketMessageRequest {
  content: string
  is_internal_note?: boolean
}

export interface AssignAgentRequest {
  agent_id: number
  is_primary?: boolean
}

// ---- WebSocket events ----

export interface ChatWsEvent {
  event: 'new_message' | 'user_typing' | 'message_read' | 'error'
  data: Record<string, unknown>
}

export interface SupportWsEvent {
  event: 'new_message' | 'agent_typing' | 'status_update' | 'error'
  data: Record<string, unknown>
}

// ---- Canned Responses (X1-103) ----

export interface CannedResponse {
  id: number
  title: string
  content: string
  category: string | null
  created_by: number
  creator_name: string | null
  tenant_id: number
  created_at: string
  updated_at: string
}

export interface CannedResponseListResponse {
  items: CannedResponse[]
  total: number
}

export interface CannedResponseCreate {
  title: string
  content: string
  category?: string | null
}

export interface CannedResponseUpdate {
  title?: string
  content?: string
  category?: string | null
}
