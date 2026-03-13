import { useEffect } from 'react'
import type { RefObject } from 'react'

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  if (target.isContentEditable) {
    return true
  }

  const tagName = target.tagName.toLowerCase()
  return tagName === 'input' || tagName === 'textarea' || tagName === 'select'
}

interface UsePreviewShortcutsParams {
  searchInputRef: RefObject<HTMLInputElement>
  editingSection: unknown
  showContentEditChooser: boolean
  handleCloseCommentPopup: () => void
  handleCloseSectionEdit: () => void
  handleCloseContentEditChooser: () => void
  navigateBetweenSections: (direction: 1 | -1) => void
  onToggleFullscreen?: () => void
}

export function usePreviewShortcuts({
  searchInputRef,
  editingSection,
  showContentEditChooser,
  handleCloseCommentPopup,
  handleCloseSectionEdit,
  handleCloseContentEditChooser,
  navigateBetweenSections,
  onToggleFullscreen,
}: UsePreviewShortcutsParams) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) {
        return
      }

      if (event.key === 'Escape') {
        handleCloseCommentPopup()
        if (editingSection) {
          handleCloseSectionEdit()
        }
        if (showContentEditChooser) {
          handleCloseContentEditChooser()
        }
        return
      }

      if (event.metaKey || event.ctrlKey || event.altKey) {
        return
      }

      if (isTypingTarget(event.target)) {
        return
      }

      const normalizedKey = event.key.toLowerCase()
      if (normalizedKey === '/') {
        if (searchInputRef.current) {
          event.preventDefault()
          searchInputRef.current.focus()
          searchInputRef.current.select()
        }
        return
      }

      if (normalizedKey === 'j') {
        event.preventDefault()
        navigateBetweenSections(1)
        return
      }

      if (normalizedKey === 'k') {
        event.preventDefault()
        navigateBetweenSections(-1)
        return
      }

      if (normalizedKey === 'f' && onToggleFullscreen) {
        event.preventDefault()
        onToggleFullscreen()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    editingSection,
    handleCloseCommentPopup,
    handleCloseContentEditChooser,
    handleCloseSectionEdit,
    navigateBetweenSections,
    onToggleFullscreen,
    searchInputRef,
    showContentEditChooser,
  ])
}
