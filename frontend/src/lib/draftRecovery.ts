export type SectionEditMode = 'edit' | 'insert' | 'full'

export interface DraftRecoveryTarget {
  documentId: number
  sectionId: string
  editMode?: SectionEditMode
}

export interface DraftRecoveryRecord {
  html: string
  baseHtml: string
  savedAt: string
}

const STORAGE_PREFIX = 'finale:draft-recovery'

function normalizeHtml(value: string): string {
  return value.replace(/>\s+</g, '><').replace(/\s+/g, ' ').trim()
}

export function isDraftRecoveryDifferent(left: string, right: string): boolean {
  return normalizeHtml(left) !== normalizeHtml(right)
}

export function getDraftRecoveryStorageKey(target: DraftRecoveryTarget): string {
  const editMode = target.editMode || 'edit'
  return `${STORAGE_PREFIX}:${target.documentId}:${editMode}:${encodeURIComponent(target.sectionId)}`
}

export function loadDraftRecovery(target: DraftRecoveryTarget): DraftRecoveryRecord | null {
  try {
    const raw = window.localStorage.getItem(getDraftRecoveryStorageKey(target))
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as Partial<DraftRecoveryRecord>
    if (
      typeof parsed.html !== 'string' ||
      typeof parsed.baseHtml !== 'string' ||
      typeof parsed.savedAt !== 'string'
    ) {
      window.localStorage.removeItem(getDraftRecoveryStorageKey(target))
      return null
    }
    return {
      html: parsed.html,
      baseHtml: parsed.baseHtml,
      savedAt: parsed.savedAt,
    }
  } catch {
    return null
  }
}

export function saveDraftRecovery(
  target: DraftRecoveryTarget,
  record: DraftRecoveryRecord,
): void {
  try {
    window.localStorage.setItem(
      getDraftRecoveryStorageKey(target),
      JSON.stringify(record),
    )
  } catch {
    // Ignore quota and storage access failures.
  }
}

export function clearDraftRecovery(target: DraftRecoveryTarget): void {
  try {
    window.localStorage.removeItem(getDraftRecoveryStorageKey(target))
  } catch {
    // Ignore storage access failures.
  }
}
