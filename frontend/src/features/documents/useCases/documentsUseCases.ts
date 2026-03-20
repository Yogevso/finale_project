import { api } from '@/lib/api'
import {
  normalizeAudienceFormPayload,
  validateAudienceFormPayload,
} from '@/features/documents/forms'
import type {
  Company,
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
  categoryFilter: string
  companyIdFilter: number | null
  dateFrom: string
  dateTo: string
}

export type DocumentUploadMetadataInput = {
  title: string
  description: string
  category: string
  platform?: string
  releaseBranch: string
  tags: string
  dueDate?: string | null
  status?: DocumentStatus
  visibility?: DocumentVisibility
  companyIds?: number[]
  releaseNotesFile?: File | null
  contentFile?: File | null
}

export type DocumentsUseCasesClient = Pick<
  typeof api,
  | 'archiveDocument'
  | 'createDocument'
  | 'createVersion'
  | 'deleteDocument'
  | 'generateWordAttachment'
  | 'getAssignedCompanies'
  | 'getDocument'
  | 'getDocumentCalendarExport'
  | 'getDocuments'
  | 'getVersion'
  | 'getVersions'
  | 'restoreDocument'
  | 'updateDocument'
  | 'uploadDocument'
>

export type UploadDocumentOptions = Parameters<DocumentsUseCasesClient['uploadDocument']>[2]

export const DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES = '.docx,.pptx,.pdf'
export const DOCUMENT_UPLOAD_MAX_SIZE_BYTES = 10 * 1024 * 1024

export const DOCUMENT_UPLOAD_ALLOWED_MIME_TYPES = new Set([
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/pdf',
])

export const DOCUMENT_UPLOAD_ALLOWED_EXTENSIONS = new Set(['.docx', '.pptx', '.pdf'])

export function buildDocumentsListQueryParams(filters: DocumentListFilters): DocumentQueryParams {
  return {
    page: filters.page,
    page_size: filters.pageSize,
    search: filters.search || undefined,
    status: filters.statusFilter || undefined,
    visibility: filters.visibilityFilter || undefined,
    category: filters.categoryFilter || undefined,
    company_id: filters.companyIdFilter ?? undefined,
    date_from: filters.dateFrom || undefined,
    date_to: filters.dateTo || undefined,
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
    return 'Only DOCX and PPTX files are allowed'
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

function getUsableVersionContent(content?: string | null): string | null {
  if (!content) {
    return null
  }

  const trimmed = content.trim()
  if (!trimmed || trimmed.toLowerCase().startsWith('uploaded from file:')) {
    return null
  }

  return trimmed
}

function requirePlatform(formData: Pick<DocumentCreateFormData, 'platform' | 'platform_id'>) {
  if (!formData.platform_id && !formData.platform?.trim()) {
    throw new Error('Platform is required.')
  }
}

async function getLatestDuplicateContent(
  client: Pick<DocumentsUseCasesClient, 'getVersion' | 'getVersions'>,
  documentId: number,
): Promise<string> {
  const versionsResponse = await client.getVersions(documentId)
  const versionsWithContent = versionsResponse.items.filter((version) =>
    Boolean(getUsableVersionContent(version.content)),
  )

  const publishedVersion = versionsWithContent
    .filter((version) => version.is_published)
    .sort(
      (left, right) =>
        new Date(right.published_at || right.created_at).getTime() -
        new Date(left.published_at || left.created_at).getTime(),
    )[0]
  const latestVersion = versionsWithContent.sort(
    (left, right) =>
      new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  )[0]
  let versionToUse = publishedVersion || latestVersion

  if (!versionToUse && versionsResponse.items.length > 0) {
    const prioritizedIds = [
      ...new Set([
        ...versionsResponse.items
          .filter((version) => version.is_published)
          .sort(
            (left, right) =>
              new Date(right.published_at || right.created_at).getTime() -
              new Date(left.published_at || left.created_at).getTime(),
          )
          .map((version) => version.id),
        ...versionsResponse.items
          .sort(
            (left, right) =>
              new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
          )
          .map((version) => version.id),
      ]),
    ]

    for (const versionId of prioritizedIds) {
      const version = await client.getVersion(documentId, versionId)
      if (getUsableVersionContent(version.content)) {
        versionToUse = version
        break
      }
    }
  }

  return getUsableVersionContent(versionToUse?.content) || ''
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
    platform: toOptionalString(input.platform || ''),
    release_branch: toOptionalString(input.releaseBranch),
    tags: toOptionalString(input.tags),
    due_date: input.dueDate || undefined,
    status: input.status,
    visibility: audience.visibility,
    company_ids: audience.company_ids.length > 0 ? audience.company_ids : undefined,
    release_notes: input.releaseNotesFile ?? undefined,
    content_file: input.contentFile ?? undefined,
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

    archiveDocument(documentId: number) {
      return client.archiveDocument(documentId)
    },

    restoreDocument(documentId: number) {
      return client.restoreDocument(documentId)
    },

    getDocumentCalendarExport(documentId: number) {
      return client.getDocumentCalendarExport(documentId)
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
      requirePlatform(formData)

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
        topic: formData.topic,
        platform: formData.platform?.trim(),
        platform_id: formData.platform_id,
        release_branch: formData.release_branch,
        tags: formData.tags,
        due_date: formData.due_date || undefined,
        parent_id: formData.parent_id,
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

    async loadDuplicateDocumentDraft(documentId: number): Promise<DocumentCreateFormData> {
      const document = await client.getDocument(documentId)
      const assignedCompanies: Company[] =
        document.visibility === 'company' ? await client.getAssignedCompanies(documentId) : []
      const content = await getLatestDuplicateContent(client, documentId)

      return {
        title: `Copy of ${document.title}`,
        description: document.description ?? '',
        status: 'draft',
        visibility: document.visibility,
        company_ids: assignedCompanies.map((company) => company.id),
        category: document.category ?? '',
        topic: document.topic ?? '',
        platform: document.platform ?? '',
        platform_id: document.platform_id ?? undefined,
        release_branch: document.release_branch ?? '',
        tags: document.tags ?? '',
        due_date: document.due_date ?? '',
        content,
        parent_id: document.id,
      }
    },

    async uploadDocument(
      file: File,
      metadata: DocumentUploadMetadataInput,
      options?: UploadDocumentOptions,
    ): Promise<Document> {
      if (!metadata.platform?.trim()) {
        throw new Error('Platform is required.')
      }

      const audienceValidationIssue = validateAudienceFormPayload({
        visibility: metadata.visibility,
        company_ids: metadata.companyIds,
      })
      if (audienceValidationIssue) {
        throw new Error(audienceValidationIssue.message)
      }

      return await client.uploadDocument(file, toUploadMetadata(metadata), options)
    },
  }
}

export const documentsUseCases = createDocumentsUseCases()
