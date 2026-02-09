export type ReadingWidth = 'reading' | 'fluid'

const STORAGE_KEY = 'doc_reading_width'

export const getReadingWidth = (fallback: ReadingWidth = 'reading'): ReadingWidth => {
  if (typeof window === 'undefined') return fallback
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'reading' || stored === 'fluid' ? stored : fallback
}

export const setReadingWidth = (value: ReadingWidth) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, value)
}
