import { useEffect, useMemo } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import {
  getPreferredPreviewAttachment,
  resolveSelectedAttachment,
} from '@/lib/attachmentSelection'
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
}

export function usePreviewSource({
  attachments,
  selectedAttachment,
  setSelectedAttachment,
  inlineContent,
  readerHtmlContent,
  readerStatus,
}: UsePreviewSourceParams) {
  const previewableAttachments = useMemo(
    () => getPreviewableAttachments(attachments),
    [attachments],
  )

  useEffect(() => {
    const nextSelection = resolveSelectedAttachment(
      previewableAttachments,
      selectedAttachment,
      getPreferredPreviewAttachment,
    )
    if (nextSelection !== selectedAttachment) {
      setSelectedAttachment(nextSelection)
    }
  }, [previewableAttachments, selectedAttachment, setSelectedAttachment])

  const previewSource: PreviewSourceKind = readerHtmlContent
    ? 'reader'
    : inlineContent
      ? 'inline'
      : 'none'
  const activeHtmlContent = readerHtmlContent || inlineContent
  const showingReaderView = selectedAttachment !== null && previewSource === 'reader'
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
