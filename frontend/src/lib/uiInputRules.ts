export const DOCUMENT_INPUT_LIMITS = {
  title: 160,
  description: 1000,
  category: 80,
  topic: 80,
  platform: 80,
  releaseBranch: 40,
  tags: 200,
  templateName: 120,
  templateDescription: 320,
  filterSearch: 120,
  filterCategory: 80,
  savedViewName: 80,
} as const

export const COMMUNICATION_INPUT_LIMITS = {
  chatMessage: 2000,
  supportReply: 2000,
  feedbackContent: 2000,
  feedbackResponse: 2000,
  visibilityReason: 280,
} as const

export function normalizeSingleLineInput(value: string | null | undefined, maxLength: number): string {
  const normalized = String(value ?? '')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  return normalized.slice(0, maxLength)
}

export function normalizeMultilineInput(value: string | null | undefined, maxLength: number): string {
  const normalized = String(value ?? '')
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map((line) => line.replace(/[ \t]+$/g, ''))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return normalized.slice(0, maxLength)
}

export function normalizeCommaSeparatedInput(value: string | null | undefined, maxLength: number): string {
  const seen = new Set<string>()
  const items: string[] = []

  for (const rawItem of String(value ?? '').split(',')) {
    const item = normalizeSingleLineInput(rawItem, maxLength)
    if (!item) {
      continue
    }

    const normalizedKey = item.toLowerCase()
    if (seen.has(normalizedKey)) {
      continue
    }

    const nextValue = items.length === 0 ? item : `${items.join(', ')}, ${item}`
    if (nextValue.length > maxLength) {
      break
    }

    seen.add(normalizedKey)
    items.push(item)
  }

  return items.join(', ')
}

export function normalizeFileStem(fileName: string | null | undefined, maxLength: number): string {
  const strippedExtension = String(fileName ?? '').replace(/\.[^/.]+$/, '')
  return normalizeSingleLineInput(strippedExtension, maxLength)
}
