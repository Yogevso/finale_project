import { useCallback, useEffect, useState } from 'react'
import type { Attachment } from '@/types'
import { resolveSectionPageStart, type TocSection } from '@/pages/document-detail/helpers/previewHelpers'

interface UseOutlineNavigationParams {
  selectedAttachment: Attachment | null
}

export function useOutlineNavigation({ selectedAttachment }: UseOutlineNavigationParams) {
  const [readerCurrentPage, setReaderCurrentPage] = useState<number | null>(null)
  const [activeHeading, setActiveHeading] = useState<string | null>(null)

  useEffect(() => {
    setReaderCurrentPage(null)
    setActiveHeading(null)
  }, [selectedAttachment?.id])

  const navigateReaderToSection = useCallback(
    (item: TocSection, behavior: ScrollBehavior = 'smooth') => {
      const anchorId = item.anchorId || `heading-${item.index}`
      const targetElement = document.getElementById(anchorId)
      const pageStart = resolveSectionPageStart(item)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior, block: 'start' })
        setActiveHeading(targetElement.id)
      } else {
        setActiveHeading(anchorId)
      }

      if (pageStart) {
        setReaderCurrentPage(pageStart)
      }
    },
    [],
  )

  return {
    readerCurrentPage,
    activeHeading,
    setReaderCurrentPage,
    setActiveHeading,
    navigateReaderToSection,
  }
}
