const STORAGE_KEY = 'doc_comments_sidebar_collapsed'

export const getCommentsSidebarCollapsed = (fallback = false): boolean => {
  if (typeof window === 'undefined') return fallback
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === null ? fallback : stored === '1'
}

export const setCommentsSidebarCollapsed = (value: boolean) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, value ? '1' : '0')
}
