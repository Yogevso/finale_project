import { getDomParser } from '@/env/dom'
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
  replaceAnchorId?: string
  replaceStartIndex?: number
  replaceNodeCount?: number
}

export interface SectionHtmlMatch {
  element: HTMLElement
  topLevelElement: HTMLElement
  topLevelIndex: number
}

function normalizeSectionLabel(value: string | undefined): string {
  return (value || '').trim().replace(/\s+/g, ' ').toLowerCase()
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
        anchorId: item.anchor_id || `page-${pageStart}`,
        pageStart,
        pageEnd: item.page_end ?? null,
      }
    })
    .filter((item) => item.text.trim().length > 0)
}

export function getEditableHtmlRoot(doc: Document): HTMLElement {
  const root = doc.body.firstElementChild
  if (doc.body.children.length === 1 && root?.classList.contains('docx-document')) {
    return root as HTMLElement
  }

  return doc.body
}

function getTopLevelEditableChild(element: HTMLElement, root: HTMLElement): HTMLElement | null {
  let current: HTMLElement | null = element
  while (current && current.parentElement && current.parentElement !== root) {
    current = current.parentElement
  }

  return current?.parentElement === root ? current : null
}

export function findSectionMatchInRoot(
  root: HTMLElement,
  section: Pick<TocSection, 'anchorId' | 'text'>,
  options?: { minTopLevelIndex?: number; maxTopLevelIndex?: number },
): SectionHtmlMatch | null {
  const doc = root.ownerDocument
  const topLevelElements = Array.from(root.children) as HTMLElement[]
  const minTopLevelIndex = options?.minTopLevelIndex ?? -1
  const maxTopLevelIndex = options?.maxTopLevelIndex ?? Number.POSITIVE_INFINITY
  const genericPageAnchor = parsePageFromAnchorId(section.anchorId)

  if (section.anchorId && !genericPageAnchor) {
    const byId = doc.getElementById(section.anchorId)
    if (byId instanceof HTMLElement) {
      const topLevelElement = getTopLevelEditableChild(byId, root)
      if (topLevelElement) {
        const topLevelIndex = topLevelElements.indexOf(topLevelElement)
        if (topLevelIndex > minTopLevelIndex && topLevelIndex < maxTopLevelIndex) {
          return { element: byId, topLevelElement, topLevelIndex }
        }
      }
    }
  }

  const normalizedLabel = normalizeSectionLabel(section.text)
  if (!normalizedLabel) {
    return null
  }

  const candidates = Array.from(
    root.querySelectorAll<HTMLElement>(
      'h1, h2, h3, h4, h5, h6, li, p, dt, dd, figcaption, summary, td, th, strong, b, table',
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
    if (tagName === 'table') {
      return 3
    }
    return 4
  }

  let bestMatch:
    | {
        element: HTMLElement
        topLevelElement: HTMLElement
        topLevelIndex: number
        score: number
        semanticRank: number
        domIndex: number
      }
    | null = null

  for (const [domIndex, element] of candidates.entries()) {
    const topLevelElement = getTopLevelEditableChild(element, root)
    if (!topLevelElement) {
      continue
    }

    const topLevelIndex = topLevelElements.indexOf(topLevelElement)
    if (topLevelIndex <= minTopLevelIndex || topLevelIndex >= maxTopLevelIndex) {
      continue
    }

    const label = normalizeSectionLabel(element.textContent || undefined)
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
      topLevelElement,
      topLevelIndex,
      score,
      semanticRank: getSemanticRank(element),
      domIndex,
    }

    if (
      !bestMatch ||
      candidate.score < bestMatch.score ||
      (candidate.score === bestMatch.score &&
        candidate.semanticRank < bestMatch.semanticRank) ||
      (candidate.score === bestMatch.score &&
        candidate.semanticRank === bestMatch.semanticRank &&
        candidate.topLevelIndex < bestMatch.topLevelIndex) ||
      (candidate.score === bestMatch.score &&
        candidate.semanticRank === bestMatch.semanticRank &&
        candidate.topLevelIndex === bestMatch.topLevelIndex &&
        candidate.domIndex < bestMatch.domIndex)
    ) {
      bestMatch = candidate
    }
  }

  if (!bestMatch) {
    return null
  }

  return {
    element: bestMatch.element,
    topLevelElement: bestMatch.topLevelElement,
    topLevelIndex: bestMatch.topLevelIndex,
  }
}

export function filterOutlineSectionsByHtml(
  outlineSections: TocSection[],
  html: string,
): TocSection[] {
  if (outlineSections.length === 0 || !html.trim()) {
    return outlineSections
  }

  const parser = getDomParser()
  const doc = parser.parseFromString(html, 'text/html')
  const root = getEditableHtmlRoot(doc)
  let previousTopLevelIndex = -1

  return outlineSections.flatMap((section) => {
    const match = findSectionMatchInRoot(root, section, {
      minTopLevelIndex: previousTopLevelIndex,
    })

    if (!match) {
      return []
    }

    previousTopLevelIndex = match.topLevelIndex

    return [
      {
        ...section,
        anchorId: match.element.id || section.anchorId,
      },
    ]
  })
}

function removeSectionFromTextMap(
  map: Map<string, TocSection[]>,
  section: TocSection,
) {
  const textKey = normalizeSectionLabel(section.text)
  if (!textKey) {
    return
  }

  const existing = map.get(textKey)
  if (!existing) {
    return
  }

  const remaining = existing.filter((candidate) => candidate !== section)
  if (remaining.length === 0) {
    map.delete(textKey)
  } else {
    map.set(textKey, remaining)
  }
}

export function mergeTocSections(
  outlineSections: TocSection[],
  htmlSections: TocSection[],
): TocSection[] {
  if (outlineSections.length === 0) {
    return htmlSections
  }

  if (htmlSections.length === 0) {
    return outlineSections
  }

  const remainingHtmlById = new Map<string, TocSection>()
  const remainingHtmlByText = new Map<string, TocSection[]>()

  htmlSections.forEach((section) => {
    if (section.anchorId) {
      remainingHtmlById.set(section.anchorId, section)
    }
    const textKey = normalizeSectionLabel(section.text)
    if (!textKey) {
      return
    }
    const existing = remainingHtmlByText.get(textKey) || []
    existing.push(section)
    remainingHtmlByText.set(textKey, existing)
  })

  const usedHtmlSections = new Set<TocSection>()

  const mergedOutlineSections = outlineSections.map((section) => {
    let htmlMatch: TocSection | undefined
    if (section.anchorId) {
      htmlMatch = remainingHtmlById.get(section.anchorId)
    }

    if (!htmlMatch) {
      const textKey = normalizeSectionLabel(section.text)
      const textMatches = remainingHtmlByText.get(textKey)
      htmlMatch = textMatches?.shift()
      if (textMatches && textMatches.length === 0) {
        remainingHtmlByText.delete(textKey)
      }
    }

    if (!htmlMatch) {
      return section
    }

    usedHtmlSections.add(htmlMatch)

    if (htmlMatch.anchorId) {
      remainingHtmlById.delete(htmlMatch.anchorId)
    }
    removeSectionFromTextMap(remainingHtmlByText, htmlMatch)

    return {
      ...htmlMatch,
      id: section.id,
      text: section.text,
      level: section.level,
      index: section.index,
      anchorId: htmlMatch.anchorId || section.anchorId,
      pageStart: section.pageStart ?? htmlMatch.pageStart,
      pageEnd: section.pageEnd ?? htmlMatch.pageEnd,
    }
  })

  const unmatchedHtmlSections = htmlSections.filter((section) => !usedHtmlSections.has(section))

  return [...mergedOutlineSections, ...unmatchedHtmlSections]
}

export function parsePageFromAnchorId(anchorId?: string | null): number | null {
  if (!anchorId) return null
  const normalizedAnchorParts = anchorId
    .trim()
    .toLowerCase()
    .split('-')
    .filter(Boolean)
  const genericPageToken =
    normalizedAnchorParts.length === 2
      ? normalizedAnchorParts[0] === 'page'
      : normalizedAnchorParts.length === 3 && normalizedAnchorParts[1] === 'page'
  if (genericPageToken) {
    const parsed = Number(normalizedAnchorParts[normalizedAnchorParts.length - 1])
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
  const documentRef = container.ownerDocument
  const nodeFilter = documentRef.defaultView?.NodeFilter ?? NodeFilter
  const walker = documentRef.createTreeWalker(container, nodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      if (!node.nodeValue || !node.nodeValue.trim()) return nodeFilter.FILTER_REJECT
      const parent = (node as Text).parentElement
      if (!parent) return nodeFilter.FILTER_REJECT
      if (parent.tagName === 'MARK') return nodeFilter.FILTER_REJECT
      return nodeFilter.FILTER_ACCEPT
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

    const fragment = documentRef.createDocumentFragment()
    let lastIndex = 0
    let match
    while ((match = regex.exec(text)) !== null) {
      const start = match.index
      const end = start + match[0].length
      if (start > lastIndex) {
        fragment.appendChild(documentRef.createTextNode(text.slice(lastIndex, start)))
      }
      const mark = documentRef.createElement('mark')
      mark.className = 'doc-highlight'
      mark.textContent = text.slice(start, end)
      fragment.appendChild(mark)
      lastIndex = end
    }
    if (lastIndex < text.length) {
      fragment.appendChild(documentRef.createTextNode(text.slice(lastIndex)))
    }
    node.parentNode?.replaceChild(fragment, node)
  })
}

export function clearHighlights(container: HTMLElement) {
  const documentRef = container.ownerDocument
  container.querySelectorAll('mark.doc-highlight').forEach((mark) => {
    const parent = mark.parentNode
    if (!parent) return
    parent.replaceChild(documentRef.createTextNode(mark.textContent || ''), mark)
    parent.normalize()
  })
}

/**
 * Detect whether an <ol> looks like a table-of-contents list.
 * TOC lists typically have items ending with page numbers (e.g. "Changes 40").
 */
function looksLikeTocList(ol: Element): boolean {
  const items = ol.querySelectorAll('li')
  if (items.length === 0) return false
  let pageNumberCount = 0
  items.forEach((li) => {
    // Only check direct text, ignoring nested lists
    const text = (li.childNodes[0]?.textContent || '').trim()
    if (/\d{1,4}\s*$/.test(text)) {
      pageNumberCount++
    }
  })
  return pageNumberCount >= items.length * 0.4
}

/**
 * Remove inline table of contents from the parsed document.
 * Matches a "Contents" heading/paragraph followed by consecutive <ol> TOC lists.
 */
function removeInlineToc(doc: Document): void {
  const root = doc.body.firstElementChild?.classList.contains('docx-document')
    ? doc.body.firstElementChild
    : doc.body

  const children = Array.from(root.children) as HTMLElement[]
  for (let i = 0; i < children.length; i++) {
    const el = children[i]
    const text = el.textContent?.trim().toLowerCase() || ''

    // Match "Contents" heading (h1-h6) or paragraph — text may be wrapped in bold/italic
    const isContentsHeading =
      (/^h[1-6]$/.test(el.tagName.toLowerCase()) || el.tagName.toLowerCase() === 'p') &&
      /^\s*contents\s*$/i.test(text)

    if (!isContentsHeading) continue

    // Found "Contents" — remove it and all consecutive TOC elements after it
    const toRemove: HTMLElement[] = [el]
    for (let j = i + 1; j < children.length; j++) {
      const next = children[j]
      const tag = next.tagName.toLowerCase()
      if (tag === 'ol' && looksLikeTocList(next)) {
        toRemove.push(next)
      } else if (tag === 'p' && !next.textContent?.trim()) {
        // Skip empty paragraphs between TOC lists
        toRemove.push(next)
      } else if (tag === 'p' && /\d{1,4}\s*$/.test(next.textContent?.trim() || '')) {
        // Standalone TOC entry paragraph ending with page number
        toRemove.push(next)
      } else {
        break
      }
    }

    // Only remove if we found at least one TOC list after the heading
    if (toRemove.length > 1) {
      toRemove.forEach((node) => node.remove())
    }
    break
  }
}

export function processHtmlIntoSections(html: string): { html: string; sections: TocSection[] } {
  const sanitizedHtml = sanitizeHtmlForPreview(html)
  const parser = getDomParser()
  const doc = parser.parseFromString(sanitizedHtml, 'text/html')

  // Remove inline table of contents from the document body.
  // The TOC is typically a heading/paragraph containing "Contents" followed by
  // ordered lists whose items end with page numbers (e.g. "40", "41").
  removeInlineToc(doc)

  const sections: TocSection[] = []
  const rootElement = doc.body.firstElementChild
  const elements = resolveSectionElements(doc)

  if (
    doc.body.children.length === 1 &&
    rootElement?.classList.contains('pptx-presentation')
  ) {
    Array.from(rootElement.children)
      .filter((element) => element.classList.contains('pptx-slide'))
      .forEach((slide, index) => {
        const title = slide.querySelector('h1, h2, h3, h4, h5, h6')
        const sectionId =
          title?.getAttribute('id') || slide.getAttribute('id') || `slide-${index + 1}`
        const titleText = title?.textContent?.trim() || `Slide ${index + 1}`
        const level = title ? parseInt(title.tagName.charAt(1), 10) : 2
        sections.push({
          id: `section-${index}-${titleText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`,
          text: titleText,
          level: Number.isFinite(level) ? level : 2,
          html: slide.outerHTML,
          index,
          anchorId: sectionId,
        })
      })

    return {
      html: doc.body.innerHTML,
      sections,
    }
  }

  const tocHeadingTags = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

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

function resolveSectionElements(doc: Document): Element[] {
  if (doc.body.children.length !== 1) {
    return Array.from(doc.body.children)
  }

  const root = doc.body.firstElementChild
  if (!root) {
    return []
  }

  if (root.classList.contains('docx-document')) {
    return Array.from(root.children)
  }

  return Array.from(doc.body.children)
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
