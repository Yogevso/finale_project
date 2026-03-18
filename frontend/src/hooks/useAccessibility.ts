import { useEffect, useRef, useCallback } from 'react'

/**
 * AC-009: Focus trapping hook for modals and dialogs.
 *
 * Traps Tab/Shift+Tab within the referenced container, handles Escape to close,
 * and returns focus to the previously-focused element on unmount.
 */
export function useFocusTrap(onClose?: () => void) {
  const containerRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement | null

    // Focus the first focusable element inside the trap
    const timer = setTimeout(() => {
      const first = getFocusableElements(containerRef.current)?.[0]
      first?.focus()
    }, 0)

    return () => {
      clearTimeout(timer)
      // Return focus to the element that opened the dialog
      previousFocusRef.current?.focus()
    }
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
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

  return { containerRef, handleKeyDown }
}

function getFocusableElements(container: HTMLElement | null): HTMLElement[] | null {
  if (!container) return null
  const elements = container.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )
  return Array.from(elements).filter((el) => el.offsetParent !== null)
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
