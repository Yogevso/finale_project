import { useCallback, useState } from 'react'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'

export function useAttachmentDownload(documentId: number) {
  const [downloadingAttachmentId, setDownloadingAttachmentId] = useState<number | null>(null)

  const downloadAttachment = useCallback(
    async (attachment: Attachment) => {
      setDownloadingAttachmentId(attachment.id)

      try {
        const blob = await api.getAttachmentBlob(documentId, attachment.id)
        const objectUrl = window.URL.createObjectURL(blob)
        const anchor = window.document.createElement('a')
        anchor.href = objectUrl
        anchor.download = attachment.original_filename || attachment.filename
        window.document.body.appendChild(anchor)
        anchor.click()
        anchor.remove()
        window.URL.revokeObjectURL(objectUrl)
      } finally {
        setDownloadingAttachmentId((currentId) =>
          currentId === attachment.id ? null : currentId,
        )
      }
    },
    [documentId],
  )

  return {
    downloadingAttachmentId,
    downloadAttachment,
  }
}
