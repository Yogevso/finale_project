import type {
  CollaborationSnapshotListResponseDto,
  CollaborationTokenResponseDto,
  DocumentDetailPageBundleDto,
  DocumentListResponseDto,
  RbacPoliciesResponseDto,
  ReviewListResponseDto,
  UserDto,
} from '@/lib/api/dto'
import type { DocumentDto } from '@/lib/api/dto'

const DEFAULT_TIMESTAMP = '2026-01-01T00:00:00Z'

export function buildUserDto(overrides: Partial<UserDto> = {}): UserDto {
  return {
    id: 7,
    email: 'editor@example.com',
    username: 'editor',
    full_name: 'Editor',
    role: 'editor',
    is_active: true,
    created_at: DEFAULT_TIMESTAMP,
    updated_at: DEFAULT_TIMESTAMP,
    ...overrides,
  }
}

export function buildDocumentDto(overrides: Partial<DocumentDto> = {}): DocumentDto {
  return {
    id: 42,
    title: 'Safety Manual',
    document_number: 'DOC-42',
    description: 'Safety baseline',
    status: 'draft',
    visibility: 'internal',
    category: 'Ops',
    tags: null,
    created_by: 1,
    created_at: DEFAULT_TIMESTAMP,
    updated_at: DEFAULT_TIMESTAMP,
    ...overrides,
  }
}

export function buildReviewListResponseDto(
  overrides: Partial<ReviewListResponseDto> = {},
): ReviewListResponseDto {
  return {
    items: [],
    total: 0,
    page: 1,
    per_page: 20,
    has_more: false,
    ...overrides,
  }
}

export function buildDocumentListResponseDto(
  overrides: Partial<DocumentListResponseDto> = {},
): DocumentListResponseDto {
  return {
    items: [buildDocumentDto()],
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1,
    ...overrides,
  }
}

export function buildDocumentDetailPageBundleDto(
  overrides: Partial<DocumentDetailPageBundleDto> = {},
): DocumentDetailPageBundleDto {
  return {
    document: buildDocumentDto(),
    attachments: [],
    assigned_companies: [],
    review_history: buildReviewListResponseDto(),
    ...overrides,
  }
}

export function buildRbacPoliciesResponseDto(
  overrides: Partial<RbacPoliciesResponseDto> = {},
): RbacPoliciesResponseDto {
  return {
    policies: [
      {
        role: 'manager',
        permissions: ['view_internal_docs', 'edit_document'],
      },
    ],
    ...overrides,
  }
}

export function buildCollaborationSnapshotListResponseDto(
  overrides: Partial<CollaborationSnapshotListResponseDto> = {},
): CollaborationSnapshotListResponseDto {
  return {
    document_id: 42,
    snapshots: [
      {
        id: 1,
        document_id: 42,
        snapshot_type: 'manual_save',
        name: 'S1',
        description: null,
        state_size: 100,
        created_by: 7,
        created_by_username: 'editor',
        session_id: null,
        is_pinned: false,
        expires_at: null,
        created_at: DEFAULT_TIMESTAMP,
      },
    ],
    total: 1,
    has_more: false,
    ...overrides,
  }
}

export function buildCollaborationTokenResponseDto(
  overrides: Partial<CollaborationTokenResponseDto> = {},
): CollaborationTokenResponseDto {
  return {
    token: 'token-42',
    document_id: 42,
    permissions: ['write'],
    websocket_url: 'ws://localhost:8002/document/42',
    expires_in: 3600,
    ...overrides,
  }
}
