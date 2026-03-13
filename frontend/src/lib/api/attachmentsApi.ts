import type {
  Attachment,
  AttachmentReaderViewResponse,
  AttachmentUploadResponse,
  MessageResponse,
} from '@/types'
import {
  type AttachmentDto,
  type AttachmentReaderViewResponseDto,
  type AttachmentUploadResponseDto,
  type MessageResponseDto,
  mapAttachmentReaderViewResponseDto,
  mapAttachmentUploadResponseDto,
  mapAttachmentsDto,
  mapMessageResponseDto,
} from './dto'
import { API_BASE_URL } from './httpClient'
import type { ApiHttpClient, Constructor } from './httpClient'

export const AttachmentsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getAttachments(documentId: number): Promise<Attachment[]> {
      const { data } = await this.client.get<AttachmentDto[]>(`/documents/${documentId}/attachments`)
      return mapAttachmentsDto(data)
    }

    async uploadAttachment(documentId: number, file: File): Promise<AttachmentUploadResponse> {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await this.client.post<AttachmentUploadResponseDto>(
        `/documents/${documentId}/attachments`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      return mapAttachmentUploadResponseDto(data)
    }

    async deleteAttachment(documentId: number, attachmentId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(
        `/documents/${documentId}/attachments/${attachmentId}`,
      )
      return mapMessageResponseDto(data)
    }

    getAttachmentDownloadUrl(documentId: number, attachmentId: number): string {
      const token = this.resolveAttachmentAccessToken()
      const base = `${API_BASE_URL}/documents/${documentId}/attachments/${attachmentId}/download`
      if (token) {
        return `${base}?token=${encodeURIComponent(token)}`
      }
      return base
    }

    async getAttachmentReaderView(
      documentId: number,
      attachmentId: number,
      options?: { retry?: boolean },
    ): Promise<AttachmentReaderViewResponse> {
      const { data } = await this.client.get<AttachmentReaderViewResponseDto>(
        `/documents/${documentId}/attachments/${attachmentId}/reader-view`,
        {
          params: options?.retry ? { retry: true } : undefined,
        },
      )
      return mapAttachmentReaderViewResponseDto(data)
    }

    async retryAttachmentReaderView(
      documentId: number,
      attachmentId: number,
    ): Promise<AttachmentReaderViewResponse> {
      const { data } = await this.client.post<AttachmentReaderViewResponseDto>(
        `/documents/${documentId}/attachments/${attachmentId}/reader-view/retry`,
      )
      return mapAttachmentReaderViewResponseDto(data)
    }

    async getAttachmentBlob(documentId: number, attachmentId: number): Promise<Blob> {
      const response = await this.client.get(
        `/documents/${documentId}/attachments/${attachmentId}/download`,
        { responseType: 'blob' },
      )
      return response.data
    }
  }
