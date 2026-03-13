export type DocumentFontSize = 'small' | 'default' | 'large'
export type DocumentTheme = 'light' | 'sepia' | 'dark'

const FONT_SIZE_STORAGE_KEY = 'doc-font-size'
const THEME_STORAGE_KEY = 'doc-theme'

export const DOCUMENT_FONT_SIZE_VALUES: Record<DocumentFontSize, string> = {
  small: '0.9rem',
  default: '1rem',
  large: '1.15rem',
}

export const DOCUMENT_THEME_CLASS_NAMES: Record<DocumentTheme, string> = {
  light: 'document-preview-paper--light',
  sepia: 'document-preview-paper--sepia',
  dark: 'document-preview-paper--dark',
}

export const getDocumentFontSize = (
  fallback: DocumentFontSize = 'default',
): DocumentFontSize => {
  if (typeof window === 'undefined') {
    return fallback
  }

  const stored = window.localStorage.getItem(FONT_SIZE_STORAGE_KEY)
  return stored === 'small' || stored === 'default' || stored === 'large' ? stored : fallback
}

export const setDocumentFontSize = (value: DocumentFontSize) => {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(FONT_SIZE_STORAGE_KEY, value)
}

export const getDocumentTheme = (fallback: DocumentTheme = 'light'): DocumentTheme => {
  if (typeof window === 'undefined') {
    return fallback
  }

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
  return stored === 'light' || stored === 'sepia' || stored === 'dark' ? stored : fallback
}

export const setDocumentTheme = (value: DocumentTheme) => {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(THEME_STORAGE_KEY, value)
}

export const getDocumentThemeClassName = (value: DocumentTheme): string =>
  DOCUMENT_THEME_CLASS_NAMES[value]
