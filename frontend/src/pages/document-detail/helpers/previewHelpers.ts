import { sanitizeHtmlForPreview } from '@/lib/htmlSanitizer'
import type { AttachmentOutlineItem } from '@/types'

export interface TocSection {
  id: string
  text: string
  level: number
  html: string
  index: number
  anchorId?: string
  pageStart?: number
  pageEnd?: number | null
}

export type SectionEditMode = 'edit' | 'insert' | 'full'

export interface SectionEditTarget extends TocSection {
  editMode?: SectionEditMode
  insertAfterIndex?: number
  fromChooser?: boolean
}

export function mapOutlineItemsToSections(items: AttachmentOutlineItem[] = []): TocSection[] {
  return items
    .map((item, index) => {
      const pageStart = item.page_start || item.page
      return {
        id: item.id || `toc-${index}`,
        text: item.title,
        level: Math.max(1, item.level || 1),
        html: '',
        index,
        anchorId: item.anchor_id || `pdf-page-${pageStart}`,
        pageStart,
        pageEnd: item.page_end ?? null,
      }
    })
    .filter((item) => item.text.trim().length > 0)
}

export function parsePageFromAnchorId(anchorId?: string | null): number | null {
  if (!anchorId) return null
  const pdfPageMatch = anchorId.match(/^pdf-page-(\d+)$/i)
  if (pdfPageMatch) {
    const parsed = Number(pdfPageMatch[1])
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null
  }
  const readerPageMatch = anchorId.match(/^reader-p(\d+)-/i)
  if (readerPageMatch) {
    const parsed = Number(readerPageMatch[1])
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null
  }
  return null
}

export function resolveSectionPageStart(item: TocSection): number | null {
  const explicitPage = Number(item.pageStart || 0)
  if (Number.isFinite(explicitPage) && explicitPage > 0) {
    return explicitPage
  }
  return parsePageFromAnchorId(item.anchorId)
}

export function getUsableVersionContent(content?: string | null): string | null {
  if (!content) return null
  const trimmed = content.trim()
  if (!trimmed || trimmed.toLowerCase().startsWith('uploaded from file:')) {
    return null
  }
  return trimmed
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function applyHighlights(container: HTMLElement, searchTerm: string) {
  clearHighlights(container)
  const term = searchTerm.trim()
  if (!term) return

  const regex = new RegExp(escapeRegExp(term), 'gi')
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT
      const parent = (node as Text).parentElement
      if (!parent) return NodeFilter.FILTER_REJECT
      if (parent.tagName === 'MARK') return NodeFilter.FILTER_REJECT
      return NodeFilter.FILTER_ACCEPT
    },
  })

  const textNodes: Text[] = []
  let current = walker.nextNode()
  while (current) {
    textNodes.push(current as Text)
    current = walker.nextNode()
  }

  textNodes.forEach((node) => {
    const text = node.nodeValue
    if (!text) return
    if (!regex.test(text)) return
    regex.lastIndex = 0

    const fragment = document.createDocumentFragment()
    let lastIndex = 0
    let match
    while ((match = regex.exec(text)) !== null) {
      const start = match.index
      const end = start + match[0].length
      if (start > lastIndex) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, start)))
      }
      const mark = document.createElement('mark')
      mark.className = 'doc-highlight'
      mark.textContent = text.slice(start, end)
      fragment.appendChild(mark)
      lastIndex = end
    }
    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)))
    }
    node.parentNode?.replaceChild(fragment, node)
  })
}

export function clearHighlights(container: HTMLElement) {
  container.querySelectorAll('mark.doc-highlight').forEach((mark) => {
    const parent = mark.parentNode
    if (!parent) return
    parent.replaceChild(document.createTextNode(mark.textContent || ''), mark)
    parent.normalize()
  })
}

export function processHtmlIntoSections(html: string): { html: string; sections: TocSection[] } {
  const sanitizedHtml = sanitizeHtmlForPreview(html)
  const parser = new DOMParser()
  const doc = parser.parseFromString(sanitizedHtml, 'text/html')
  const elements = Array.from(doc.body.children)
  const sections: TocSection[] = []
  const allHeadingTags = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
  const hasPrimaryHeadings = elements.some((element) => {
    const tagName = element.tagName.toLowerCase()
    return tagName === 'h1' || tagName === 'h2' || tagName === 'h3'
  })
  const tocHeadingTags = hasPrimaryHeadings ? new Set(['h1', 'h2', 'h3']) : allHeadingTags

  let currentSection: { heading: Element | null; content: Element[] } = { heading: null, content: [] }

  elements.forEach((element) => {
    const tagName = element.tagName.toLowerCase()
    if (tocHeadingTags.has(tagName)) {
      if (currentSection.heading) {
        sections.push(buildSectionEntry(currentSection, sections.length))
      }

      const existingHeadingId = element.getAttribute('id')
      const headingAnchorId = existingHeadingId || `heading-${sections.length}`
      element.setAttribute('id', headingAnchorId)
      element.classList.add('scroll-mt-4')
      currentSection = { heading: element, content: [] }
    } else if (currentSection.heading) {
      currentSection.content.push(element)
    }
  })

  if (currentSection.heading) {
    sections.push(buildSectionEntry(currentSection, sections.length))
  }

  if (sections.length === 0) {
    const fullDocumentHtml = doc.body.innerHTML.trim()
    if (fullDocumentHtml) {
      sections.push({
        id: 'section-0-full-document',
        text: 'Document Content',
        level: 1,
        html: fullDocumentHtml,
        index: 0,
        anchorId: 'document-content-area',
      })
    }
  }

  return {
    html: doc.body.innerHTML,
    sections,
  }
}

function buildSectionEntry(
  section: { heading: Element | null; content: Element[] },
  index: number,
): TocSection {
  const heading = section.heading as Element
  const headingText = heading.textContent?.trim() || 'Section'
  const headingAnchorId = heading.getAttribute('id') || `heading-${index}`
  const sectionHtml = [heading.outerHTML, ...section.content.map((entry) => entry.outerHTML)].join('\n')

  return {
    id: `section-${index}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`,
    text: headingText,
    level: parseInt(heading.tagName.charAt(1), 10),
    html: sectionHtml,
    index,
    anchorId: headingAnchorId,
  }
}
