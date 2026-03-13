import { useCallback, useEffect, useRef, useState } from 'react'
import type { RefObject, UIEvent } from 'react'
import { api } from '@/lib/api'
import {
  resolveSectionPageStart,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers'

interface UsePreviewProgressParams {
  documentId: number
  activeHtmlContent: string | null
  selectedAttachmentId: number | null
  previewPaneRef: RefObject<HTMLDivElement>
  activeHeading: string | null
  setActiveHeading: (headingId: string | null) => void
  sections: TocSection[]
  readerCurrentPage: number | null
  setReaderCurrentPage: (page: number | null) => void
  onScrollProgress?: (progress: number) => void
  hasUser: boolean
}

export function usePreviewProgress({
  documentId,
  activeHtmlContent,
  selectedAttachmentId,
  previewPaneRef,
  activeHeading,
  setActiveHeading,
  sections,
  readerCurrentPage,
  setReaderCurrentPage,
  onScrollProgress,
  hasUser,
}: UsePreviewProgressParams) {
  const [previewScrollProgress, setPreviewScrollProgress] = useState(0)
  const restoredProgressKeyRef = useRef<string | null>(null)

  const handleScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      const container = event.currentTarget
      const scrollTop = container.scrollTop
      const scrollHeight = container.scrollHeight - container.clientHeight
      const containerRect = container.getBoundingClientRect()

      if (scrollHeight > 0) {
        const progress = Math.min(100, Math.round((scrollTop / scrollHeight) * 100))
        setPreviewScrollProgress(progress)
        onScrollProgress?.(progress)
      } else {
        setPreviewScrollProgress(0)
      }

      const headings = container.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]')
      let currentActive: string | null = null

      headings.forEach((heading) => {
        const rect = heading.getBoundingClientRect()
        if (rect.top <= containerRect.top + 100) {
          currentActive = heading.id
        }
      })

      if (currentActive && currentActive !== activeHeading) {
        setActiveHeading(currentActive)
        const currentSection = sections.find((section) => section.anchorId === currentActive)
        const pageStart = currentSection ? resolveSectionPageStart(currentSection) : null
        if (pageStart && pageStart !== readerCurrentPage) {
          setReaderCurrentPage(pageStart)
        }
      }
    },
    [
      activeHeading,
      onScrollProgress,
      readerCurrentPage,
      sections,
      setActiveHeading,
      setReaderCurrentPage,
    ],
  )

  useEffect(() => {
    if (!activeHtmlContent) {
      setPreviewScrollProgress(0)
      return
    }

    setPreviewScrollProgress(0)
  }, [activeHtmlContent])

  useEffect(() => {
    if (!hasUser || !activeHtmlContent || !previewPaneRef.current) {
      return
    }

    const restoreKey = `${documentId}:${selectedAttachmentId ?? 'inline'}`
    if (restoredProgressKeyRef.current === restoreKey) {
      return
    }
    restoredProgressKeyRef.current = restoreKey

    let cancelled = false
    let rafOne: number | null = null
    let rafTwo: number | null = null

    api
      .getDocumentProgress(documentId)
      .then((progress) => {
        if (cancelled || !progress.has_progress || !previewPaneRef.current) {
          return
        }

        rafOne = window.requestAnimationFrame(() => {
          rafTwo = window.requestAnimationFrame(() => {
            const pane = previewPaneRef.current
            if (!pane) {
              return
            }

            const scrollRange = pane.scrollHeight - pane.clientHeight
            if (scrollRange <= 0) {
              return
            }

            pane.scrollTop = Math.round(scrollRange * (progress.progress_percent / 100))
            setPreviewScrollProgress(progress.progress_percent)
            onScrollProgress?.(progress.progress_percent)
          })
        })
      })
      .catch(() => {
        // Ignore unavailable progress records or role-gated responses.
      })

    return () => {
      cancelled = true
      if (rafOne !== null) {
        window.cancelAnimationFrame(rafOne)
      }
      if (rafTwo !== null) {
        window.cancelAnimationFrame(rafTwo)
      }
    }
  }, [
    activeHtmlContent,
    documentId,
    hasUser,
    onScrollProgress,
    previewPaneRef,
    selectedAttachmentId,
  ])

  return {
    previewScrollProgress,
    handleScroll,
  }
}
