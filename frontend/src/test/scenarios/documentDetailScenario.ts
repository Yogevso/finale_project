import type {
  CollaborationTokenResponseDto,
  DocumentDetailPageBundleDto,
} from '@/lib/api/dto'
import {
  buildCollaborationTokenResponseDto,
  buildDocumentDetailPageBundleDto,
  buildDocumentDto,
  buildReviewListResponseDto,
} from '@/test/factories/apiDto'

export interface DocumentDetailCollaborationScenario {
  documentId: number
  bundle: DocumentDetailPageBundleDto
  collabToken: CollaborationTokenResponseDto
}

export function buildDocumentDetailCollaborationScenario(
  documentId: number = 42,
): DocumentDetailCollaborationScenario {
  const document = buildDocumentDto({
    id: documentId,
    title: 'Safety Manual',
    document_number: `DOC-${documentId}`,
    description: 'Safety baseline',
    status: 'draft',
    visibility: 'internal',
    category: 'Ops',
    tags: null,
    created_by: 1,
  })

  const bundle = buildDocumentDetailPageBundleDto({
    document,
    attachments: [
      {
        id: 100,
        document_id: documentId,
        filename: 'spec.pdf',
        original_filename: 'spec.pdf',
        file_size: 128,
        size_bytes: 128,
        mime_type: 'application/pdf',
        uploaded_by: 1,
        uploaded_at: '2026-01-01T00:00:00Z',
      },
    ],
    assigned_companies: [
      {
        id: 12,
        name: 'Scenario Co',
        slug: 'scenario-co',
        is_active: true,
        company_type: 'customer',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        user_count: 2,
        owned_document_count: 1,
        assigned_document_count: 3,
        customer_visible_document_count: 3,
        document_count: 3,
      },
    ],
    review_history: buildReviewListResponseDto({
      items: [
        {
          id: 901,
          document_id: documentId,
          version_id: 77,
          submitted_by: 1,
          reviewed_by: null,
          status: 'pending',
          message: 'Please review section updates.',
          review_comments: null,
          submitted_at: '2026-01-01T00:00:00Z',
          reviewed_at: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      has_more: false,
    }),
  })

  const collabToken = buildCollaborationTokenResponseDto({
    token: `token-${documentId}`,
    document_id: documentId,
    websocket_url: `ws://localhost:8002/document/${documentId}`,
    permissions: ['write'],
  })

  return {
    documentId,
    bundle,
    collabToken,
  }
}
