import { useEffect, useRef, useCallback, type KeyboardEvent as ReactKeyboardEvent } from 'react'

/**
 * AC-009: Focus trapping hook for modals and dialogs.
 *
 * Traps Tab/Shift+Tab within the referenced container, handles Escape to close,
 * and returns focus to the previously-focused element on unmount.
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(onClose?: () => void) {
  const containerRef = useRef<T>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  const handleTrapKeyDown = useCallback(
    (e: KeyboardEvent | ReactKeyboardEvent) => {
      if (e.key === 'Escape' && onClose) {
        e.stopPropagation()
        onClose()
        return
      }

      if (e.key !== 'Tab') return

      const focusable = getFocusableElements(containerRef.current)
      if (!focusable || focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    },
    [onClose],
  )

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement | null

    // Focus the first focusable element inside the trap
    const timer = setTimeout(() => {
      const first = getFocusableElements(containerRef.current)?.[0]
      first?.focus()
    }, 0)

    const handleNativeKeyDown = (event: KeyboardEvent) => {
      handleTrapKeyDown(event)
    }

    const container = containerRef.current
    container?.addEventListener('keydown', handleNativeKeyDown)

    return () => {
      clearTimeout(timer)
      container?.removeEventListener('keydown', handleNativeKeyDown)
      // Return focus to the element that opened the dialog
      previousFocusRef.current?.focus()
    }
  }, [handleTrapKeyDown])

  return { containerRef, handleKeyDown: handleTrapKeyDown }
}

function getFocusableElements(container: HTMLElement | null): HTMLElement[] | null {
  if (!container) return null
  const elements = container.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )
  return Array.from(elements).filter((el) => {
    if (el.hasAttribute('hidden') || el.getAttribute('aria-hidden') === 'true') {
      return false
    }

    if (el.getAttribute('tabindex') === '-1') {
      return false
    }

    return !el.closest('[hidden], [aria-hidden="true"]')
  })
}

/**
 * AC-010: Announce route changes to screen readers.
 *
 * Returns a ref to attach to an aria-live region and a function to announce text.
 */
export function useRouteAnnouncer() {
  const announcerRef = useRef<HTMLDivElement>(null)

  const announce = useCallback((message: string) => {
    if (announcerRef.current) {
      announcerRef.current.textContent = ''
      // Force screen readers to re-read by toggling content in a microtask
      requestAnimationFrame(() => {
        if (announcerRef.current) {
          announcerRef.current.textContent = message
        }
      })
    }
  }, [])

  return { announcerRef, announce }
}
