import type { Attachment } from '@/types'

export function resolveSelectedAttachment(
  attachments: Attachment[],
  selectedAttachment: Attachment | null,
  getPreferredAttachment: (items: Attachment[]) => Attachment | null,
): Attachment | null {
  if (attachments.length === 0) {
    return null
  }

  if (selectedAttachment) {
    const refreshed = attachments.find((attachment) => attachment.id === selectedAttachment.id)
    if (refreshed) {
      return refreshed
    }
  }

  return getPreferredAttachment(attachments)
}

export function getPreferredPreviewAttachment(attachments: Attachment[]): Attachment | null {
  return (
    attachments.find((attachment) => attachment.preview_pdf_status === 'ready') ||
    attachments.find((attachment) => attachment.mime_type.startsWith('application/pdf')) ||
    attachments[0] ||
    null
  )
}

export function getPreferredEditorAttachment(attachments: Attachment[]): Attachment | null {
  return (
    attachments.find(
      (attachment) =>
        attachment.mime_type === 'application/msword' ||
        attachment.mime_type ===
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ) ||
    attachments.find((attachment) => attachment.mime_type === 'application/pdf') ||
    null
  )
}
