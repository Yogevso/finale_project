import { useCallback, useState } from 'react'
import { createObjectUrl, getDocument, revokeObjectUrl } from '@/env/dom'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'

export function useAttachmentDownload(documentId: number) {
  const [downloadingAttachmentId, setDownloadingAttachmentId] = useState<number | null>(null)

  const downloadAttachment = useCallback(
    async (attachment: Attachment) => {
      setDownloadingAttachmentId(attachment.id)

      try {
        const blob = await api.getAttachmentBlob(documentId, attachment.id)
        const objectUrl = createObjectUrl(blob)
        const anchor = getDocument().createElement('a')
        anchor.href = objectUrl
        anchor.download = attachment.original_filename || attachment.filename
        getDocument().body.appendChild(anchor)
        anchor.click()
        anchor.remove()
        revokeObjectUrl(objectUrl)
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
