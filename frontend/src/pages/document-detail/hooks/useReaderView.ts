import type { Dispatch, SetStateAction } from 'react'
import type { Attachment } from '@/types'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useOutlineNavigation } from '@/pages/document-detail/hooks/useOutlineNavigation'
import { useReaderArtifact } from '@/pages/document-detail/hooks/useReaderArtifact'

interface UseReaderViewParams {
  documentId: number
  selectedAttachment: Attachment | null
  sections: TocSection[]
  setSections: Dispatch<SetStateAction<TocSection[]>>
  processHtmlWithSections: (html: string) => string
}

export function useReaderView({
  documentId,
  selectedAttachment,
  sections,
  setSections,
  processHtmlWithSections,
}: UseReaderViewParams) {
  const artifactState = useReaderArtifact({
    documentId,
    selectedAttachment,
    setSections,
    processHtmlWithSections,
  })
  const outlineNavigation = useOutlineNavigation({ selectedAttachment })

  return {
    ...artifactState,
    ...outlineNavigation,
    hasReaderSections: sections.length > 0,
  }
}
