import type {
  Attachment,
  AttachmentFidelityViewResponse,
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
import type { ApiClientBase, Constructor } from './httpClient'

export const AttachmentsApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
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

    /**
     * Get a download URL with a short-lived signed ticket (AD-002).
     */
    async getAttachmentDownloadUrl(documentId: number, attachmentId: number): Promise<string> {
      const base = `${API_BASE_URL}/documents/${documentId}/attachments/${attachmentId}/download`
      const { data } = await this.client.post<{ ticket: string; expires_in: number }>(
        '/attachments/download-ticket',
        { document_id: documentId, attachment_id: attachmentId },
      )
      return `${base}?token=${encodeURIComponent(data.ticket)}`
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

    /**
     * Page-faithful HTML for a PDF attachment. Read-only companion to the Reader View;
     * the response is rendered on demand rather than stored, so it has no DTO contract.
     */
    async getAttachmentFidelityView(
      documentId: number,
      attachmentId: number,
    ): Promise<AttachmentFidelityViewResponse> {
      const { data } = await this.client.get<AttachmentFidelityViewResponse>(
        `/documents/${documentId}/attachments/${attachmentId}/fidelity-view`,
      )
      return data
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
