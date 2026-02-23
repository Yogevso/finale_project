import type {
  Comment,
  CommentCreate,
  CommentUpdate,
  Company,
  Document,
  DocumentCreate,
  DocumentListResponse,
  DocumentQueryParams,
  DocumentUpdate,
  DocumentVisibility,
  MessageResponse,
  Version,
  VersionCreate,
  VersionListResponse,
  VersionUpdate,
} from '@/types'
import type { ApiHttpClient, Constructor } from './httpClient'

export const DocumentsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getDocuments(params?: DocumentQueryParams): Promise<DocumentListResponse> {
      const { data } = await this.client.get<DocumentListResponse>('/documents', { params })
      return data
    }

    async getDocument(id: number): Promise<Document> {
      const { data } = await this.client.get<Document>(`/documents/${id}`)
      return data
    }

    async createDocument(document: DocumentCreate): Promise<Document> {
      const { data } = await this.client.post<Document>('/documents', document)
      return data
    }

    async updateDocument(id: number, document: DocumentUpdate): Promise<Document> {
      const { data } = await this.client.put<Document>(`/documents/${id}`, document)
      return data
    }

    async deleteDocument(id: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(`/documents/${id}`)
      return data
    }

    async generateWordAttachment(documentId: number, htmlContent: string, filename?: string) {
      const { data } = await this.client.post(`/documents/${documentId}/generate-word`, {
        html_content: htmlContent,
        filename,
      })
      return data
    }

    async uploadDocument(file: File, metadata?: {
      title?: string
      description?: string
      category?: string
      release_branch?: string
      tags?: string
      document_number?: string
      version_label?: string
      visibility?: DocumentVisibility
      parent_id?: number
      topic?: string
      platform?: string
      release_notes?: File | null
      content_file?: File | null
    }): Promise<Document> {
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
      if (metadata?.parent_id) formData.append('parent_id', metadata.parent_id.toString())
      if (metadata?.topic) formData.append('topic', metadata.topic)
      if (metadata?.platform) formData.append('platform', metadata.platform)
      if (metadata?.release_notes) formData.append('release_notes', metadata.release_notes)
      if (metadata?.content_file) formData.append('content_file', metadata.content_file)

      const { data } = await this.client.post<Document>('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    }

    async getAssignedCompanies(documentId: number): Promise<{ companies: Company[] }> {
      const { data } = await this.client.get<{ companies: Company[] }>(
        `/documents/${documentId}/assigned-companies`,
      )
      return data
    }

    async assignCompanies(
      documentId: number,
      companyIds: number[],
    ): Promise<{ message: string; assigned_count: number }> {
      const { data } = await this.client.post<{ message: string; assigned_count: number }>(
        `/documents/${documentId}/assign-companies`,
        { company_ids: companyIds },
      )
      return data
    }

    async removeCompanyAssignment(documentId: number, companyId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(
        `/documents/${documentId}/assign-companies/${companyId}`,
      )
      return data
    }

    async getVersions(documentId: number): Promise<VersionListResponse> {
      const { data } = await this.client.get<VersionListResponse>(`/documents/${documentId}/versions`)
      return data
    }

    async getVersion(documentId: number, versionId: number): Promise<Version> {
      const { data } = await this.client.get<Version>(`/documents/${documentId}/versions/${versionId}`)
      return data
    }

    async createVersion(documentId: number, version: VersionCreate): Promise<Version> {
      const { data } = await this.client.post<Version>(`/documents/${documentId}/versions`, version)
      return data
    }

    async updateVersion(documentId: number, versionId: number, version: VersionUpdate): Promise<Version> {
      const { data } = await this.client.patch<Version>(
        `/documents/${documentId}/versions/${versionId}`,
        version,
      )
      return data
    }

    async publishVersion(documentId: number, versionId: number): Promise<Version> {
      const { data } = await this.client.post<Version>(
        `/documents/${documentId}/versions/${versionId}/publish`,
      )
      return data
    }

    async deleteVersion(documentId: number, versionId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(
        `/documents/${documentId}/versions/${versionId}`,
      )
      return data
    }

    async getComments(documentId: number, parentId?: number): Promise<Comment[]> {
      const params = parentId !== undefined ? { parent_id: parentId } : {}
      const { data } = await this.client.get<Comment[]>(`/documents/${documentId}/comments`, { params })
      return data
    }

    async getComment(documentId: number, commentId: number): Promise<Comment> {
      const { data } = await this.client.get<Comment>(`/documents/${documentId}/comments/${commentId}`)
      return data
    }

    async createComment(documentId: number, comment: CommentCreate): Promise<Comment> {
      const { data } = await this.client.post<Comment>(`/documents/${documentId}/comments`, comment)
      return data
    }

    async updateComment(documentId: number, commentId: number, comment: CommentUpdate): Promise<Comment> {
      const { data } = await this.client.patch<Comment>(
        `/documents/${documentId}/comments/${commentId}`,
        comment,
      )
      return data
    }

    async deleteComment(documentId: number, commentId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(
        `/documents/${documentId}/comments/${commentId}`,
      )
      return data
    }
  }

