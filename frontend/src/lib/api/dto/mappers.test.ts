import { describe, expect, it } from 'vitest'

import type {
  CollaborationSnapshotListResponseDto,
  DocumentListResponseDto,
  RbacPoliciesResponseDto,
} from './contracts'
import {
  mapCollaborationSnapshotListResponseDto,
  mapDocumentListResponseDto,
  mapRbacPoliciesResponseDto,
} from './mappers'

describe('api dto mappers', () => {
  it('maps document list payloads with nested created_by_user', () => {
    const source: DocumentListResponseDto = {
      items: [
        {
          id: 1,
          title: 'Doc',
          document_number: 'DOC-1',
          description: null,
          status: 'draft',
          visibility: 'internal',
          category: null,
          tags: null,
          created_by: 7,
          created_at: '2026-02-28T10:00:00Z',
          updated_at: '2026-02-28T11:00:00Z',
          created_by_user: {
            id: 7,
            email: 'editor@example.com',
            username: 'editor',
            full_name: 'Editor',
            role: 'editor',
            is_active: true,
            created_at: '2026-02-28T09:00:00Z',
            updated_at: '2026-02-28T09:00:00Z',
          },
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
    }

    const mapped = mapDocumentListResponseDto(source)

    expect(mapped.items).toHaveLength(1)
    expect(mapped.items[0].created_by_user?.username).toBe('editor')
    expect(mapped.total).toBe(1)
  })

  it('maps RBAC policy payloads as copied arrays', () => {
    const source: RbacPoliciesResponseDto = {
      policies: [
        {
          role: 'manager',
          permissions: ['view_internal_docs', 'edit_document'],
        },
      ],
    }

    const mapped = mapRbacPoliciesResponseDto(source)

    expect(mapped.policies).toHaveLength(1)
    expect(mapped.policies[0].role).toBe('manager')
    expect(mapped.policies[0].permissions).toEqual(['view_internal_docs', 'edit_document'])
    expect(mapped.policies[0].permissions).not.toBe(source.policies[0].permissions)
  })

  it('maps collaboration snapshot list payloads', () => {
    const source: CollaborationSnapshotListResponseDto = {
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
          created_at: '2026-02-28T10:00:00Z',
        },
      ],
      total: 1,
      has_more: false,
    }

    const mapped = mapCollaborationSnapshotListResponseDto(source)

    expect(mapped.document_id).toBe(42)
    expect(mapped.snapshots[0].name).toBe('S1')
    expect(mapped.total).toBe(1)
  })
})
