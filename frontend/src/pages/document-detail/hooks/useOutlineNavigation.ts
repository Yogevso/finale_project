import { useCallback, useEffect, useState } from 'react'
import { getDocument } from '@/env/dom'
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

  const normalizeSectionText = useCallback((value: string | null | undefined) => {
    return (value || '').trim().replace(/\s+/g, ' ').toLowerCase()
  }, [])

  const findSectionTarget = useCallback((item: TocSection): HTMLElement | null => {
    const anchorId = item.anchorId || `heading-${item.index}`
    const documentRef = getDocument()
    const contentRoot =
      documentRef.getElementById('document-content-area') ||
      documentRef.body
    const byId = documentRef.getElementById(anchorId)
    if (byId) {
      return byId
    }

    const normalizedLabel = normalizeSectionText(item.text)
    if (!normalizedLabel) {
      return null
    }

    const candidates = Array.from(
      contentRoot.querySelectorAll<HTMLElement>(
        'h1, h2, h3, h4, h5, h6, li, p, dt, dd, figcaption, summary, td, th, strong, b',
      ),
    )

    const getSemanticRank = (element: HTMLElement): number => {
      const tagName = element.tagName.toLowerCase()
      if (/^h[1-6]$/.test(tagName)) {
        return 0
      }
      if (tagName === 'li') {
        return 1
      }
      if (tagName === 'p' || tagName === 'dt' || tagName === 'dd' || tagName === 'summary') {
        return 2
      }
      if (tagName === 'figcaption' || tagName === 'strong' || tagName === 'b') {
        return 3
      }
      return 4
    }

    let bestMatch:
      | {
          element: HTMLElement
          score: number
          semanticRank: number
          domIndex: number
          length: number
        }
      | null = null

    for (const [domIndex, element] of candidates.entries()) {
      const label = normalizeSectionText(element.textContent)
      if (!label) {
        continue
      }

      let score: number | null = null
      if (label === normalizedLabel) {
        score = 0
      } else if (label.startsWith(normalizedLabel)) {
        score = 1
      } else if (label.includes(normalizedLabel)) {
        score = 2
      }

      if (score === null) {
        continue
      }

      const candidate = {
        element,
        score,
        semanticRank: getSemanticRank(element),
        domIndex,
        length: label.length,
      }
      if (
        !bestMatch ||
        candidate.score < bestMatch.score ||
        (candidate.score === bestMatch.score &&
          candidate.semanticRank < bestMatch.semanticRank) ||
        (candidate.score === bestMatch.score &&
          candidate.semanticRank === bestMatch.semanticRank &&
          candidate.domIndex > bestMatch.domIndex) ||
        (candidate.score === bestMatch.score &&
          candidate.semanticRank === bestMatch.semanticRank &&
          candidate.domIndex === bestMatch.domIndex &&
          candidate.length < bestMatch.length)
      ) {
        bestMatch = candidate
      }
    }

    if (!bestMatch) {
      return null
    }

    if (!bestMatch.element.id) {
      bestMatch.element.id = anchorId
    }

    return bestMatch.element
  }, [normalizeSectionText])

  const navigateReaderToSection = useCallback(
    (item: TocSection, behavior: ScrollBehavior = 'smooth') => {
      const anchorId = item.anchorId || `heading-${item.index}`
      const targetElement = findSectionTarget(item)
      const pageStart = resolveSectionPageStart(item)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior, block: 'start' })
        setActiveHeading(targetElement.id || anchorId)
      } else {
        setActiveHeading(anchorId)
      }

      if (pageStart) {
        setReaderCurrentPage(pageStart)
      }
    },
    [findSectionTarget],
  )

  return {
    readerCurrentPage,
    activeHeading,
    setReaderCurrentPage,
    setActiveHeading,
    navigateReaderToSection,
  }
}
