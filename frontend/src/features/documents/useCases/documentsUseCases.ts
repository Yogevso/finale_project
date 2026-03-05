import { api } from '@/lib/api'
import {
  normalizeAudienceFormPayload,
  validateAudienceFormPayload,
} from '@/features/documents/forms'
import type {
  Document,
  DocumentCreate,
  DocumentListResponse,
  DocumentQueryParams,
  DocumentStatus,
  DocumentVisibility,
  MessageResponse,
} from '@/types'

export type DocumentCreateFormData = DocumentCreate & { content?: string }

export type DocumentListFilters = {
  page: number
  pageSize: number
  search: string
  statusFilter: DocumentStatus | ''
  visibilityFilter: DocumentVisibility | ''
}

export type DocumentUploadMetadataInput = {
  title: string
  description: string
  category: string
  releaseBranch: string
  tags: string
  visibility?: DocumentVisibility
  companyIds?: number[]
}

export type DocumentsUseCasesClient = Pick<
  typeof api,
  | 'createDocument'
  | 'createVersion'
  | 'deleteDocument'
  | 'generateWordAttachment'
  | 'getDocuments'
  | 'updateDocument'
  | 'uploadDocument'
>

export const DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES = '.pdf,.doc,.docx'
export const DOCUMENT_UPLOAD_MAX_SIZE_BYTES = 10 * 1024 * 1024

export const DOCUMENT_UPLOAD_ALLOWED_MIME_TYPES = new Set([
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
])

export const DOCUMENT_UPLOAD_ALLOWED_EXTENSIONS = new Set(['.pdf', '.doc', '.docx'])

export function buildDocumentsListQueryParams(filters: DocumentListFilters): DocumentQueryParams {
  return {
    page: filters.page,
    page_size: filters.pageSize,
    search: filters.search || undefined,
    status: filters.statusFilter || undefined,
    visibility: filters.visibilityFilter || undefined,
  }
}

export function validateDocumentUploadFile(file: File): string | null {
  const mime = (file.type || '').toLowerCase()
  const extensionMatch = file.name.toLowerCase().match(/\.[^.]+$/)
  const extension = extensionMatch ? extensionMatch[0] : ''
  const isSupported =
    DOCUMENT_UPLOAD_ALLOWED_MIME_TYPES.has(mime) ||
    DOCUMENT_UPLOAD_ALLOWED_EXTENSIONS.has(extension)

  if (!isSupported) {
    return 'Only PDF and Word documents are allowed'
  }

  if (file.size > DOCUMENT_UPLOAD_MAX_SIZE_BYTES) {
    return 'File size must be less than 10MB'
  }

  return null
}

function toOptionalString(value: string): string | undefined {
  const normalized = value.trim()
  return normalized ? normalized : undefined
}

function toUploadMetadata(input: DocumentUploadMetadataInput) {
  const audience = normalizeAudienceFormPayload({
    visibility: input.visibility,
    company_ids: input.companyIds,
  })

  return {
    title: toOptionalString(input.title),
    description: toOptionalString(input.description),
    category: toOptionalString(input.category),
    release_branch: toOptionalString(input.releaseBranch),
    tags: toOptionalString(input.tags),
    visibility: audience.visibility,
    company_ids: audience.company_ids.length > 0 ? audience.company_ids : undefined,
  }
}

export function createDocumentsUseCases(client: DocumentsUseCasesClient = api) {
  return {
    listDocuments(params: DocumentQueryParams): Promise<DocumentListResponse> {
      return client.getDocuments(params)
    },

    deleteDocument(documentId: number): Promise<MessageResponse> {
      return client.deleteDocument(documentId)
    },

    updateVisibility(
      documentId: number,
      visibility: DocumentVisibility,
      ifMatch: string,
      reason: string,
      companyIds?: number[],
    ): Promise<Document> {
      const updatePayload: {
        visibility: DocumentVisibility
        reason: string
        company_ids?: number[]
      } = { visibility, reason }
      if (companyIds && companyIds.length > 0) {
        updatePayload.company_ids = companyIds
      }
      return client.updateDocument(documentId, updatePayload, ifMatch)
    },

    async createDraftDocument(
      formData: DocumentCreateFormData,
      options: { generateWord: boolean },
    ): Promise<Document> {
      const audienceValidationIssue = validateAudienceFormPayload(formData)
      if (audienceValidationIssue) {
        throw new Error(audienceValidationIssue.message)
      }

      const audience = normalizeAudienceFormPayload(formData)
      const document = await client.createDocument({
        title: formData.title,
        description: formData.description,
        status: 'draft',
        visibility: audience.visibility,
        company_ids: audience.company_ids,
        category: formData.category,
        release_branch: formData.release_branch,
        tags: formData.tags,
      })

      const content = formData.content?.trim() || ''
      if (content) {
        await client.createVersion(document.id, {
          content: formData.content,
          changes_summary: 'Initial content',
        })

        if (options.generateWord) {
          await client.generateWordAttachment(document.id, formData.content ?? '', `${formData.title}.docx`)
        }

        return document
      }

      if (options.generateWord) {
        throw new Error('Please add content before generating a Word file')
      }

      return document
    },

    async uploadDocument(file: File, metadata: DocumentUploadMetadataInput): Promise<Document> {
      const audienceValidationIssue = validateAudienceFormPayload({
        visibility: metadata.visibility,
        company_ids: metadata.companyIds,
      })
      if (audienceValidationIssue) {
        throw new Error(audienceValidationIssue.message)
      }

      return await client.uploadDocument(file, toUploadMetadata(metadata))
    },
  }
}

export const documentsUseCases = createDocumentsUseCases()
