/**
 * AC-004: Skip navigation link — "Skip to main content" visible on focus.
 * AC-010: Route announcer — announces page changes to screen readers.
 */

/**
 * Renders a skip link that is visually hidden until focused.
 * Place as the first child inside each layout component.
 */
export function SkipNavLink({ targetId = 'main-content' }: { targetId?: string }) {
  return (
    <a
      href={`#${targetId}`}
      className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[9999] focus:rounded-lg focus:bg-blue-700 focus:px-4 focus:py-2 focus:text-white focus:text-sm focus:font-semibold focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-white"
    >
      Skip to main content
    </a>
  )
}

/**
 * Visually hidden live region that announces route changes.
 * Place once in the app root and call `announce()` on navigation.
 */
export function RouteAnnouncer({ message }: { message: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  )
}
