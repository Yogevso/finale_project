export const UNTITLED_DOCUMENT_LABEL = 'Untitled document'
export const NO_DOCUMENT_DESCRIPTION_LABEL = 'No description provided'

export function getDocumentDisplayTitle(
  title: string | null | undefined,
  fallback = UNTITLED_DOCUMENT_LABEL,
): string {
  const normalized = typeof title === 'string' ? title.trim() : ''
  return normalized || fallback
}

export function getDocumentDisplayDescription(
  description: string | null | undefined,
  fallback = NO_DOCUMENT_DESCRIPTION_LABEL,
): string {
  const normalized = typeof description === 'string' ? description.trim() : ''
  return normalized || fallback
}
