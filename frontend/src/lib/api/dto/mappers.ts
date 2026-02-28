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
import type {
  CommentDto,
  DocumentCreateDto,
  DocumentDto,
  DocumentListResponseDto,
  DocumentUpdateDto,
  MessageResponseDto,
  TokenResponseDto,
  UserCreateDto,
  UserDto,
  UserUpdateDto,
  VersionCreateDto,
  VersionDto,
  VersionListResponseDto,
  VersionUpdateDto,
} from './contracts'

export function mapTokenResponseDto(dto: TokenResponseDto): TokenResponse {
  return { ...dto }
}

export function mapMessageResponseDto(dto: MessageResponseDto): MessageResponse {
  return { ...dto }
}

export function mapUserDto(dto: UserDto): User {
  return { ...dto }
}

export function mapUsersDto(dtos: UserDto[]): User[] {
  return dtos.map(mapUserDto)
}

export function toUserCreateDto(payload: {
  email: string
  username: string
  full_name: string
  password: string
  role: User['role']
  tenant_id?: number
}): UserCreateDto {
  return { ...payload }
}

export function toUserUpdateDto(payload: {
  email?: string
  full_name?: string
  role?: User['role']
  is_active?: boolean
  tenant_id?: number | null
}): UserUpdateDto {
  return { ...payload }
}

export function mapDocumentDto(dto: DocumentDto): Document {
  return {
    ...dto,
    created_by_user: dto.created_by_user ? mapUserDto(dto.created_by_user) : undefined,
  }
}

export function mapDocumentListResponseDto(
  dto: DocumentListResponseDto,
): DocumentListResponse {
  return {
    ...dto,
    items: dto.items.map(mapDocumentDto),
  }
}

export function toDocumentCreateDto(payload: DocumentCreate): DocumentCreateDto {
  return { ...payload }
}

export function toDocumentUpdateDto(payload: DocumentUpdate): DocumentUpdateDto {
  return { ...payload }
}

export function mapVersionDto(dto: VersionDto): Version {
  return {
    ...dto,
    created_by_user: dto.created_by_user ? mapUserDto(dto.created_by_user) : undefined,
    published_by_user: dto.published_by_user ? mapUserDto(dto.published_by_user) : undefined,
    latest_review: dto.latest_review ? { ...dto.latest_review } : dto.latest_review,
  }
}

export function mapVersionListResponseDto(dto: VersionListResponseDto): VersionListResponse {
  return {
    ...dto,
    items: dto.items.map(mapVersionDto),
  }
}

export function toVersionCreateDto(payload: VersionCreate): VersionCreateDto {
  return { ...payload }
}

export function toVersionUpdateDto(payload: VersionUpdate): VersionUpdateDto {
  return { ...payload }
}

export function mapCommentDto(dto: CommentDto): Comment {
  return {
    ...dto,
    user: dto.user ? { ...dto.user } : dto.user,
    replies: dto.replies.map(mapCommentDto),
  }
}

export function mapCommentsDto(dtos: CommentDto[]): Comment[] {
  return dtos.map(mapCommentDto)
}
