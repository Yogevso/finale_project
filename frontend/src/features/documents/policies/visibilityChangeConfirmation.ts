import type { DocumentVisibility } from '@/types'

const VISIBILITY_EXPOSURE_LEVEL: Record<DocumentVisibility, number> = {
  internal: 0,
  company: 1,
  public: 2,
}

const VISIBILITY_LABELS: Record<DocumentVisibility, string> = {
  internal: 'Internal',
  company: 'Company',
  public: 'Public',
}

export function requiresVisibilityChangeConfirmation(
  fromVisibility: DocumentVisibility,
  toVisibility: DocumentVisibility,
): boolean {
  if (fromVisibility === toVisibility) {
    return false
  }
  return VISIBILITY_EXPOSURE_LEVEL[toVisibility] > VISIBILITY_EXPOSURE_LEVEL[fromVisibility]
}

export function getVisibilityLabel(visibility: DocumentVisibility): string {
  return VISIBILITY_LABELS[visibility]
}
