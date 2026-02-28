import { describe, expect, it } from 'vitest'
import type {
  CollaborationTokenResponseDto,
  DocumentDetailPageBundleDto,
} from '@/lib/api/dto'
import {
  mapCollaborationTokenResponseDto,
  mapDocumentDetailPageBundleDto,
} from '@/lib/api/dto'
import contract from './backendProvider.contract.json'

describe('frontend consumer contract', () => {
  it('uses a semver contract version marker', () => {
    expect(contract.contract_version).toMatch(/^\d+\.\d+\.\d+$/)
    expect(contract.consumer).toBe('frontend')
    expect(contract.provider).toBe('backend')
  })

  it('maps collab-token fixture expected by collaboration consumers', () => {
    const fixture = contract.fixtures.collab_token_response as CollaborationTokenResponseDto

    const mapped = mapCollaborationTokenResponseDto(fixture)

    expect(mapped.document_id).toBe(42)
    expect(mapped.permissions).toEqual(['read', 'write'])
    expect(mapped.websocket_url).toContain('/document/42')
    expect(mapped.expires_in).toBe(3600)
  })

  it('maps BFF detail-page bundle fixture expected by document-detail consumers', () => {
    const fixture = contract.fixtures
      .document_detail_bundle_response as unknown as DocumentDetailPageBundleDto

    const mapped = mapDocumentDetailPageBundleDto(fixture)

    expect(mapped.document.id).toBe(42)
    expect(mapped.attachments[0].id).toBe(100)
    expect(mapped.assigned_companies[0].id).toBe(12)
    expect(mapped.review_history.items[0].status).toBe('pending')
  })
})
