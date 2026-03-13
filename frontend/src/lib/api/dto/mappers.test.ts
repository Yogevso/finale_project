import { describe, expect, it } from 'vitest'

import type {
  CollaborationSnapshotListResponseDto,
  DocumentDetailPageBundleDto,
  DocumentListResponseDto,
  RbacPoliciesResponseDto,
} from './contracts'
import {
  mapCollaborationSnapshotListResponseDto,
  mapDocumentDetailPageBundleDto,
  mapDocumentListResponseDto,
  mapRbacPoliciesResponseDto,
  toDocumentCreateDto,
  toDocumentUpdateDto,
} from './mappers'
import {
  buildCollaborationSnapshotListResponseDto,
  buildDocumentDetailPageBundleDto,
  buildDocumentDto,
  buildDocumentListResponseDto,
  buildRbacPoliciesResponseDto,
  buildUserDto,
} from '@/test/factories/apiDto'

describe('api dto mappers', () => {
  it('maps document list payloads with nested created_by_user', () => {
    const source: DocumentListResponseDto = buildDocumentListResponseDto({
      items: [
        buildDocumentDto({
          id: 1,
          title: 'Doc',
          document_number: 'DOC-1',
          description: null,
          category: null,
          created_by: 7,
          created_by_user: buildUserDto(),
        }),
      ],
    })

    const mapped = mapDocumentListResponseDto(source)

    expect(mapped.items).toHaveLength(1)
    expect(mapped.items[0].created_by_user?.username).toBe('editor')
    expect(mapped.total).toBe(1)
  })

  it('maps RBAC policy payloads as copied arrays', () => {
    const source: RbacPoliciesResponseDto = buildRbacPoliciesResponseDto()

    const mapped = mapRbacPoliciesResponseDto(source)

    expect(mapped.policies).toHaveLength(1)
    expect(mapped.policies[0].role).toBe('manager')
    expect(mapped.policies[0].permissions).toEqual(['view_internal_docs', 'edit_document'])
    expect(mapped.policies[0].permissions).not.toBe(source.policies[0].permissions)
  })

  it('maps collaboration snapshot list payloads', () => {
    const source: CollaborationSnapshotListResponseDto =
      buildCollaborationSnapshotListResponseDto()

    const mapped = mapCollaborationSnapshotListResponseDto(source)

    expect(mapped.document_id).toBe(42)
    expect(mapped.snapshots[0].name).toBe('S1')
    expect(mapped.total).toBe(1)
  })

  it('normalizes empty due dates in document write payloads', () => {
    expect(
      toDocumentCreateDto({
        title: 'Policy',
        due_date: '',
      }),
    ).toEqual({
      title: 'Policy',
      due_date: null,
    })

    expect(
      toDocumentUpdateDto({
        visibility: 'public',
        reason: 'Expand audience',
        due_date: '',
      }),
    ).toEqual({
      visibility: 'public',
      reason: 'Expand audience',
      due_date: null,
    })
  })

  it('fails loudly in development when the document detail bundle is missing required fields', () => {
    const source = buildDocumentDetailPageBundleDto({
      document: undefined,
    }) as unknown as DocumentDetailPageBundleDto

    expect(() => mapDocumentDetailPageBundleDto(source)).toThrow(
      'DTO mapping invariant failed: DocumentDetailPageBundleDto.document is required',
    )
  })
})
