import { useEffect, useMemo } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { getPreferredPreviewAttachment } from '@/lib/attachmentSelection'
import type { Attachment } from '@/types'
import {
  decidePreviewState,
  getPreviewableAttachments,
  normalizeReaderPreviewStatus,
} from '@/pages/document-detail/helpers/previewState'

type PreviewSourceKind = 'reader' | 'inline' | 'none'

interface UsePreviewSourceParams {
  attachments: Attachment[]
  selectedAttachment: Attachment | null
  setSelectedAttachment: Dispatch<SetStateAction<Attachment | null>>
  inlineContent: string | null
  readerHtmlContent: string | null
  readerStatus: Attachment['reader_html_status'] | string | null
  isInlineLoading: boolean
}

function getAttachmentSelectionKey(attachment: Attachment | null): string {
  if (!attachment) {
    return 'none'
  }

  return [
    attachment.id,
    attachment.reader_html_status || '',
    attachment.reader_toc_source || '',
    attachment.filename,
    attachment.mime_type,
    attachment.file_size,
    attachment.uploaded_at,
  ].join(':')
}

export function usePreviewSource({
  attachments,
  selectedAttachment,
  setSelectedAttachment,
  inlineContent,
  readerHtmlContent,
  readerStatus,
  isInlineLoading,
}: UsePreviewSourceParams) {
  const previewableAttachments = useMemo(
    () => getPreviewableAttachments(attachments),
    [attachments],
  )

  useEffect(() => {
    if (selectedAttachment) {
      const refreshedSelection =
        previewableAttachments.find((attachment) => attachment.id === selectedAttachment.id) || null
      if (
        getAttachmentSelectionKey(refreshedSelection) !==
        getAttachmentSelectionKey(selectedAttachment)
      ) {
        setSelectedAttachment(refreshedSelection)
      }
      return
    }

    if (inlineContent || isInlineLoading || previewableAttachments.length === 0) {
      return
    }

    const nextSelection = getPreferredPreviewAttachment(previewableAttachments)
    if (
      getAttachmentSelectionKey(nextSelection) !== getAttachmentSelectionKey(selectedAttachment)
    ) {
      setSelectedAttachment(nextSelection)
    }
  }, [inlineContent, isInlineLoading, previewableAttachments, selectedAttachment, setSelectedAttachment])

  const previewSource: PreviewSourceKind = selectedAttachment
    ? 'reader'
    : inlineContent
      ? 'inline'
      : readerHtmlContent
        ? 'reader'
        : 'none'
  const activeHtmlContent =
    previewSource === 'reader' ? readerHtmlContent : previewSource === 'inline' ? inlineContent : null
  const showingReaderView = previewSource === 'reader'
  const shouldRenderHtmlPreview = activeHtmlContent !== null
  const previewState = useMemo(
    () =>
      decidePreviewState({
        attachments,
        inlineContent: activeHtmlContent,
        readerStatus: normalizeReaderPreviewStatus(readerStatus),
      }),
    [activeHtmlContent, attachments, readerStatus],
  )

  return {
    previewSource,
    previewableAttachments,
    activeHtmlContent,
    showingReaderView,
    shouldRenderHtmlPreview,
    previewState,
  }
}
