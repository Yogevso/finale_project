import { sanitizeHtmlForPreview } from '@/lib/htmlSanitizer'

export type VersionDiffStatus = 'unchanged' | 'modified' | 'added' | 'removed'

export interface VersionDiffBlock {
  id: string
  html: string
  text: string
  signature: string
}

export interface VersionDiffRow {
  id: string
  status: VersionDiffStatus
  left: VersionDiffBlock | null
  right: VersionDiffBlock | null
}

export interface VersionDiffSummary {
  unchanged: number
  modified: number
  added: number
  removed: number
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, ' ').trim().toLowerCase()
}

function normalizeHtml(value: string): string {
  return value.replace(/>\s+</g, '><').replace(/\s+/g, ' ').trim()
}

function createTextBlock(text: string, index: number): VersionDiffBlock {
  const trimmedText = text.trim()
  return {
    id: `text-${index}`,
    html: `<p>${escapeHtml(trimmedText)}</p>`,
    text: trimmedText,
    signature: normalizeText(trimmedText),
  }
}

export function extractVersionDiffBlocks(html: string | null | undefined): VersionDiffBlock[] {
  const sanitizedHtml = sanitizeHtmlForPreview(html || '')
  const doc = new DOMParser().parseFromString(sanitizedHtml, 'text/html')
  const nodes = Array.from(doc.body.childNodes)
  const blocks: VersionDiffBlock[] = []

  nodes.forEach((node, index) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element
      const elementText = element.textContent?.replace(/\s+/g, ' ').trim() || ''
      blocks.push({
        id: element.getAttribute('id') || `block-${index}`,
        html: element.outerHTML,
        text: elementText,
        signature: normalizeText(elementText) || normalizeHtml(element.outerHTML),
      })
      return
    }

    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent?.trim() || ''
      if (text) {
        blocks.push(createTextBlock(text, index))
      }
    }
  })

  if (blocks.length > 0) {
    return blocks
  }

  const fallbackText = doc.body.textContent?.trim() || ''
  return fallbackText ? [createTextBlock(fallbackText, 0)] : []
}

function buildLcsMatrix(left: string[], right: string[]): number[][] {
  const rows = left.length + 1
  const cols = right.length + 1
  const matrix = Array.from({ length: rows }, () => Array<number>(cols).fill(0))

  for (let leftIndex = left.length - 1; leftIndex >= 0; leftIndex -= 1) {
    for (let rightIndex = right.length - 1; rightIndex >= 0; rightIndex -= 1) {
      matrix[leftIndex][rightIndex] =
        left[leftIndex] === right[rightIndex]
          ? matrix[leftIndex + 1][rightIndex + 1] + 1
          : Math.max(matrix[leftIndex + 1][rightIndex], matrix[leftIndex][rightIndex + 1])
    }
  }

  return matrix
}

function buildMatchedPairs(leftBlocks: VersionDiffBlock[], rightBlocks: VersionDiffBlock[]) {
  const leftSignatures = leftBlocks.map((block) => block.signature)
  const rightSignatures = rightBlocks.map((block) => block.signature)
  const matrix = buildLcsMatrix(leftSignatures, rightSignatures)
  const matches: Array<{ leftIndex: number; rightIndex: number }> = []

  let leftIndex = 0
  let rightIndex = 0

  while (leftIndex < leftSignatures.length && rightIndex < rightSignatures.length) {
    if (leftSignatures[leftIndex] === rightSignatures[rightIndex]) {
      matches.push({ leftIndex, rightIndex })
      leftIndex += 1
      rightIndex += 1
      continue
    }

    if (matrix[leftIndex + 1][rightIndex] >= matrix[leftIndex][rightIndex + 1]) {
      leftIndex += 1
    } else {
      rightIndex += 1
    }
  }

  return matches
}

function createSegmentRows(
  rows: VersionDiffRow[],
  leftSegment: VersionDiffBlock[],
  rightSegment: VersionDiffBlock[],
  rowOffset: number,
): number {
  const segmentLength = Math.max(leftSegment.length, rightSegment.length)
  let nextOffset = rowOffset

  for (let index = 0; index < segmentLength; index += 1) {
    const left = leftSegment[index] || null
    const right = rightSegment[index] || null
    const status: VersionDiffStatus =
      left && right ? 'modified' : left ? 'removed' : 'added'

    rows.push({
      id: `diff-${nextOffset}`,
      status,
      left,
      right,
    })
    nextOffset += 1
  }

  return nextOffset
}

export function buildVersionDiffRows(
  leftHtml: string | null | undefined,
  rightHtml: string | null | undefined,
): VersionDiffRow[] {
  const leftBlocks = extractVersionDiffBlocks(leftHtml)
  const rightBlocks = extractVersionDiffBlocks(rightHtml)
  const matches = buildMatchedPairs(leftBlocks, rightBlocks)
  const rows: VersionDiffRow[] = []

  let previousLeftIndex = 0
  let previousRightIndex = 0
  let rowOffset = 0

  matches.forEach((match) => {
    rowOffset = createSegmentRows(
      rows,
      leftBlocks.slice(previousLeftIndex, match.leftIndex),
      rightBlocks.slice(previousRightIndex, match.rightIndex),
      rowOffset,
    )

    const left = leftBlocks[match.leftIndex]
    const right = rightBlocks[match.rightIndex]
    const status: VersionDiffStatus =
      normalizeHtml(left.html) === normalizeHtml(right.html) ? 'unchanged' : 'modified'

    rows.push({
      id: `diff-${rowOffset}`,
      status,
      left,
      right,
    })
    rowOffset += 1
    previousLeftIndex = match.leftIndex + 1
    previousRightIndex = match.rightIndex + 1
  })

  createSegmentRows(
    rows,
    leftBlocks.slice(previousLeftIndex),
    rightBlocks.slice(previousRightIndex),
    rowOffset,
  )

  return rows
}

export function summarizeVersionDiff(rows: VersionDiffRow[]): VersionDiffSummary {
  return rows.reduce<VersionDiffSummary>(
    (summary, row) => {
      summary[row.status] += 1
      return summary
    },
    {
      unchanged: 0,
      modified: 0,
      added: 0,
      removed: 0,
    },
  )
}
