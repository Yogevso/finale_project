import { useCallback, useState } from 'react'
import { createObjectUrl, getDocument, revokeObjectUrl } from '@/env/dom'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'

export function useAttachmentDownload(documentId: number) {
  const [downloadingAttachmentId, setDownloadingAttachmentId] = useState<number | null>(null)

  const downloadAttachment = useCallback(
    async (attachment: Attachment) => {
      setDownloadingAttachmentId(attachment.id)
      let objectUrl: string | null = null

      try {
        let url: string
        try {
          // H-23: Use HMAC-signed download ticket instead of direct blob fetch
          url = await api.getAttachmentDownloadUrl(documentId, attachment.id)
        } catch {
          // Fallback to authenticated blob fetch when ticket issuance is unavailable.
          const blob = await api.getAttachmentBlob(documentId, attachment.id)
          objectUrl = createObjectUrl(blob)
          url = objectUrl
        }

        const anchor = getDocument().createElement('a')
        anchor.href = url
        anchor.download = attachment.original_filename || attachment.filename
        getDocument().body.appendChild(anchor)
        anchor.click()
        anchor.remove()
      } finally {
        if (objectUrl) {
          revokeObjectUrl(objectUrl)
        }
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
