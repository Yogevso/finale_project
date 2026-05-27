import type { AxiosProgressEvent } from 'axios'
import type {
  DocumentArchiveResult,
  DocumentCalendarExport,
  BulkDocumentMetadataUpdate,
  BulkDocumentMetadataUpdateResponse,
  Comment,
  CommentCreate,
  CommentUpdate,
  Company,
  Document,
  DuplicateCheckResponse,
  DocumentCreate,
  DocumentDashboardStats,
  DocumentListResponse,
  DocumentWatchResponse,
  DocumentWatchStatus,
  DocumentQueryParams,
  DocumentUpdate,
  DocumentVisibility,
  MessageResponse,
  Version,
  VersionCreate,
  VersionListResponse,
  VersionUpdate,
} from '@/types'
import { isFrontendFeatureEnabled } from '@/config/featureFlags'
import {
  type CommentDto,
  type CompanyDto,
  type DocumentCreateDto,
  type DocumentDto,
  type DocumentListResponseDto,
  type DocumentUpdateDto,
  type MessageResponseDto,
  type VersionCreateDto,
  type VersionDto,
  type VersionListResponseDto,
  type VersionUpdateDto,
  mapCommentDto,
  mapCommentsDto,
  mapCompanyDto,
  mapDocumentDto,
  mapDocumentListResponseDto,
  mapMessageResponseDto,
  mapVersionDto,
  mapVersionListResponseDto,
  toDocumentCreateDto,
  toDocumentUpdateDto,
  toVersionCreateDto,
  toVersionUpdateDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export type DocumentUploadApiOptions = {
  onUploadProgress?: (event: AxiosProgressEvent) => void
}

export const DocumentsApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    async getDocuments(params?: DocumentQueryParams): Promise<DocumentListResponse> {
      const { data } = await this.client.get<DocumentListResponseDto>('/documents', { params })
      return mapDocumentListResponseDto(data)
    }

    async getDeletedDocuments(params?: DocumentQueryParams): Promise<DocumentListResponse> {
      const { data } = await this.client.get<DocumentListResponseDto>('/documents/deleted', { params })
      return mapDocumentListResponseDto(data)
    }

    async getDocumentStats(): Promise<DocumentDashboardStats> {
      const { data } = await this.client.get<DocumentDashboardStats>('/documents/stats')
      return data
    }

    async getDocumentTags(query?: string, limit: number = 20): Promise<string[]> {
      const { data } = await this.client.get<{ items: string[] }>('/documents/tags', {
        params: { q: query, limit },
      })
      return data.items
    }

    async checkDocumentDuplicates(
      title: string,
      options?: { threshold?: number; limit?: number },
    ): Promise<DuplicateCheckResponse> {
      const { data } = await this.client.get<DuplicateCheckResponse>('/documents/duplicate-check', {
        params: { title, ...options },
      })
      return data
    }

    async bulkUpdateDocumentMetadata(
      payload: BulkDocumentMetadataUpdate,
    ): Promise<BulkDocumentMetadataUpdateResponse> {
      const { data } = await this.client.post<BulkDocumentMetadataUpdateResponse>(
        '/documents/bulk-metadata',
        payload,
      )
      return data
    }

    async getDocument(id: number): Promise<Document> {
      const { data } = await this.client.get<DocumentDto>(`/documents/${id}`)
      return mapDocumentDto(data)
    }

    async createDocument(document: DocumentCreate): Promise<Document> {
      const payload = toDocumentCreateDto(document)
      const { data } = await this.client.post<DocumentDto>('/documents', payload as DocumentCreateDto)
      return mapDocumentDto(data)
    }

    async updateDocument(
      id: number,
      document: DocumentUpdate,
      ifMatch?: string,
    ): Promise<Document> {
      const payload = toDocumentUpdateDto(document)
      const headers =
        ifMatch && isFrontendFeatureEnabled('optimisticConcurrencyHeaders')
          ? { 'If-Match': ifMatch }
          : undefined
      const { data } = await this.client.put<DocumentDto>(
        `/documents/${id}`,
        payload as DocumentUpdateDto,
        { headers },
      )
      return mapDocumentDto(data)
    }

    async deleteDocument(id: number, ifMatch?: string): Promise<MessageResponse> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.delete<MessageResponseDto>(`/documents/${id}`, { headers })
      return mapMessageResponseDto(data)
    }

    async restoreDeletedDocument(id: number, ifMatch?: string): Promise<Document> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.post<DocumentDto>(`/documents/${id}/restore-deleted`, null, { headers })
      return mapDocumentDto(data)
    }

    async purgeDocument(id: number, ifMatch?: string): Promise<MessageResponse> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.delete<MessageResponseDto>(`/documents/${id}/purge`, { headers })
      return mapMessageResponseDto(data)
    }

    async archiveDocument(id: number, ifMatch?: string): Promise<DocumentArchiveResult> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.post<DocumentArchiveResult>(`/documents/${id}/archive`, null, { headers })
      return data
    }

    async restoreDocument(id: number, ifMatch?: string): Promise<DocumentArchiveResult> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.post<DocumentArchiveResult>(`/documents/${id}/restore`, null, { headers })
      return data
    }

    async getDocumentCalendarExport(id: number): Promise<DocumentCalendarExport> {
      const { data } = await this.client.get<DocumentCalendarExport>(`/documents/${id}/calendar-export`)
      return data
    }

    async generateWordAttachment(documentId: number, htmlContent: string, filename?: string) {
      const { data } = await this.client.post(`/documents/${documentId}/generate-word`, {
        html_content: htmlContent,
        filename,
      })
      return data
    }

    async exportDocument(documentId: number, format: 'pdf' | 'docx' | 'pptx'): Promise<Blob> {
      const { data } = await this.client.get<Blob>(`/documents/${documentId}/export`, {
        params: { format },
        responseType: 'blob',
      })
      return data
    }

    async uploadDocument(
      file: File,
      metadata?: {
        title?: string
        description?: string
        category?: string
        release_branch?: string
        tags?: string
        document_number?: string
        version_label?: string
        visibility?: DocumentVisibility
        company_ids?: number[]
        parent_id?: number
        topic?: string
        platform?: string
        due_date?: string | null
        status?: string
        release_notes?: File | null
        content_file?: File | null
        pdf_conversion_target?: string
      },
      options?: DocumentUploadApiOptions,
    ): Promise<Document> {
      const formData = new FormData()
      formData.append('file', file)
      if (metadata?.title) formData.append('title', metadata.title)
      if (metadata?.description) formData.append('description', metadata.description)
      if (metadata?.category) formData.append('category', metadata.category)
      if (metadata?.release_branch) formData.append('release_branch', metadata.release_branch)
      if (metadata?.tags) formData.append('tags', metadata.tags)
      if (metadata?.document_number) formData.append('document_number', metadata.document_number)
      if (metadata?.version_label) formData.append('version_label', metadata.version_label)
      if (metadata?.visibility) formData.append('visibility', metadata.visibility)
      if (metadata?.company_ids && metadata.company_ids.length > 0) {
        for (const companyId of metadata.company_ids) {
          formData.append('company_ids', String(companyId))
        }
      }
      if (metadata?.parent_id) formData.append('parent_id', metadata.parent_id.toString())
      if (metadata?.topic) formData.append('topic', metadata.topic)
      if (metadata?.platform) formData.append('platform', metadata.platform)
      if (metadata?.due_date) formData.append('due_date', metadata.due_date)
      if (metadata?.status) formData.append('status', metadata.status)
      if (metadata?.release_notes) formData.append('release_notes', metadata.release_notes)
      if (metadata?.content_file) formData.append('content_file', metadata.content_file)
      if (metadata?.pdf_conversion_target) {
        formData.append('pdf_conversion_target', metadata.pdf_conversion_target)
      }

      const { data } = await this.client.post<DocumentDto>('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: options?.onUploadProgress,
      })
      return mapDocumentDto(data)
    }

    async getAssignedCompanies(documentId: number): Promise<Company[]> {
      const { data } = await this.client.get<CompanyDto[]>(
        `/documents/${documentId}/assigned-companies`,
      )
      return data.map(mapCompanyDto)
    }

    async getDocumentWatchStatus(documentId: number): Promise<DocumentWatchStatus> {
      const { data } = await this.client.get<DocumentWatchStatus>(
        `/documents/${documentId}/watch-status`,
      )
      return data
    }

    async watchDocument(documentId: number): Promise<DocumentWatchResponse> {
      const { data } = await this.client.post<DocumentWatchResponse>(
        `/documents/${documentId}/watch`,
      )
      return data
    }

    async unwatchDocument(documentId: number): Promise<DocumentWatchResponse> {
      const { data } = await this.client.delete<DocumentWatchResponse>(
        `/documents/${documentId}/watch`,
      )
      return data
    }

    async assignCompanies(
      documentId: number,
      companyIds: number[],
      ifMatch?: string,
    ): Promise<MessageResponse> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.post<MessageResponseDto>(
        `/documents/${documentId}/assign-companies`,
        { company_ids: companyIds },
        { headers },
      )
      return mapMessageResponseDto(data)
    }

    async removeCompanyAssignment(
      documentId: number,
      companyId: number,
      ifMatch?: string,
    ): Promise<MessageResponse> {
      const headers = ifMatch ? { 'If-Match': ifMatch } : undefined
      const { data } = await this.client.delete<MessageResponseDto>(
        `/documents/${documentId}/assign-companies/${companyId}`,
        { headers },
      )
      return mapMessageResponseDto(data)
    }

    async getVersions(documentId: number): Promise<VersionListResponse> {
      const { data } = await this.client.get<VersionListResponseDto>(
        `/documents/${documentId}/versions`,
      )
      return mapVersionListResponseDto(data)
    }

    async getVersion(documentId: number, versionId: number): Promise<Version> {
      const { data } = await this.client.get<VersionDto>(`/documents/${documentId}/versions/${versionId}`)
      return mapVersionDto(data)
    }

    async createVersion(documentId: number, version: VersionCreate): Promise<Version> {
      const payload = toVersionCreateDto(version)
      const { data } = await this.client.post<VersionDto>(
        `/documents/${documentId}/versions`,
        payload as VersionCreateDto,
      )
      return mapVersionDto(data)
    }

    async updateVersion(
      documentId: number,
      versionId: number,
      version: VersionUpdate,
      ifMatch?: string,
    ): Promise<Version> {
      const payload = toVersionUpdateDto(version)
      const headers =
        ifMatch && isFrontendFeatureEnabled('optimisticConcurrencyHeaders')
          ? { 'If-Match': ifMatch }
          : undefined
      const { data } = await this.client.patch<VersionDto>(
        `/documents/${documentId}/versions/${versionId}`,
        payload as VersionUpdateDto,
        { headers },
      )
      return mapVersionDto(data)
    }

    async publishVersion(documentId: number, versionId: number): Promise<Version> {
      const { data } = await this.client.post<VersionDto>(
        `/documents/${documentId}/versions/${versionId}/publish`,
      )
      return mapVersionDto(data)
    }

    async deleteVersion(documentId: number, versionId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(
        `/documents/${documentId}/versions/${versionId}`,
      )
      return mapMessageResponseDto(data)
    }

    async getComments(
      documentId: number,
      parentId?: number,
      reviewId?: number,
    ): Promise<Comment[]> {
      const params: { parent_id?: number; review_id?: number } = {}
      if (parentId !== undefined) {
        params.parent_id = parentId
      }
      if (reviewId !== undefined) {
        params.review_id = reviewId
      }
      const { data } = await this.client.get<CommentDto[] | { items: CommentDto[] }>(
        `/documents/${documentId}/comments`,
        {
          params,
        },
      )
      const payload = Array.isArray(data)
        ? data
        : Array.isArray((data as { items?: CommentDto[] }).items)
          ? ((data as { items?: CommentDto[] }).items as CommentDto[])
          : []
      return mapCommentsDto(payload)
    }

    async getComment(documentId: number, commentId: number): Promise<Comment> {
      const { data } = await this.client.get<CommentDto>(
        `/documents/${documentId}/comments/${commentId}`,
      )
      return mapCommentDto(data)
    }

    async createComment(documentId: number, comment: CommentCreate): Promise<Comment> {
      const { data } = await this.client.post<CommentDto>(`/documents/${documentId}/comments`, comment)
      return mapCommentDto(data)
    }

    async updateComment(documentId: number, commentId: number, comment: CommentUpdate): Promise<Comment> {
      const { data } = await this.client.patch<CommentDto>(
        `/documents/${documentId}/comments/${commentId}`,
        comment,
      )
      return mapCommentDto(data)
    }

    async deleteComment(documentId: number, commentId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(
        `/documents/${documentId}/comments/${commentId}`,
      )
      return mapMessageResponseDto(data)
    }
  }
