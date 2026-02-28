import type {
  Comment,
  Document,
  DocumentCreate,
  DocumentListResponse,
  DocumentUpdate,
  MessageResponse,
  TokenResponse,
  User,
  Version,
  VersionCreate,
  VersionListResponse,
  VersionUpdate,
} from '@/types'

// Transport DTO contracts intentionally live at the API boundary.
// They can diverge from domain/UI types over time without forcing
// broad call-site edits across the frontend.
export type TokenResponseDto = TokenResponse
export type MessageResponseDto = MessageResponse

export type UserDto = User
export type UserCreateDto = {
  email: string
  username: string
  full_name: string
  password: string
  role: User['role']
  tenant_id?: number
}
export type UserUpdateDto = {
  email?: string
  full_name?: string
  role?: User['role']
  is_active?: boolean
  tenant_id?: number | null
}

export type DocumentDto = Document
export type DocumentCreateDto = DocumentCreate
export type DocumentUpdateDto = DocumentUpdate
export type DocumentListResponseDto = DocumentListResponse

export type VersionDto = Version
export type VersionCreateDto = VersionCreate
export type VersionUpdateDto = VersionUpdate
export type VersionListResponseDto = VersionListResponse

export type CommentDto = Comment
