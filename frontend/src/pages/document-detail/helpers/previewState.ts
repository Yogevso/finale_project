import type { Attachment } from '@/types'

export const PREVIEWABLE_ATTACHMENT_MIME_TYPES = new Set([
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
])

export type ReaderPreviewStatus = 'idle' | 'pending' | 'ready' | 'failed'
export type PreviewState = 'NO_CONTENT' | 'DOWNLOAD_ONLY' | 'LOADING' | 'READY' | 'ERROR'

export function isPreviewableAttachment(attachment: Attachment): boolean {
  return PREVIEWABLE_ATTACHMENT_MIME_TYPES.has((attachment.mime_type || '').toLowerCase())
}

export function getPreviewableAttachments(attachments: Attachment[]): Attachment[] {
  return attachments.filter(isPreviewableAttachment)
}

export function normalizeReaderPreviewStatus(status: string | null | undefined): ReaderPreviewStatus {
  if (status === 'ready') {
    return 'ready'
  }

  if (status === 'failed') {
    return 'failed'
  }

  if (status === 'pending' || status === 'processing') {
    return 'pending'
  }

  return 'idle'
}

export function decidePreviewState(params: {
  attachments: Attachment[]
  inlineContent: string | null
  readerStatus: ReaderPreviewStatus
}): PreviewState {
  const { attachments, inlineContent, readerStatus } = params
  const hasInlineContent = Boolean(inlineContent?.trim())

  if (hasInlineContent) {
    return 'READY'
  }

  if (attachments.length === 0) {
    return 'NO_CONTENT'
  }

  if (getPreviewableAttachments(attachments).length === 0) {
    return 'DOWNLOAD_ONLY'
  }

  if (readerStatus === 'failed' || readerStatus === 'ready') {
    return 'ERROR'
  }

  return 'LOADING'
}
