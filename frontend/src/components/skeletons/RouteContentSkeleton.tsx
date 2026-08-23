import { CardSkeleton } from './CardSkeleton'

/**
 * What a page looks like while its module arrives.
 *
 * The route fallback used to be a spinner on an empty `min-h-screen`, which replaced the
 * header and the navigation as well as the content - so every navigation threw the whole
 * window away and rebuilt it. The shell is already on screen and already correct; only
 * the content is missing, so only the content is drawn as absent.
 */
export function RouteContentSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading page">
      <div className="space-y-3">
        <div className="h-3 w-24 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
        <div className="h-8 w-64 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
        <div className="h-4 w-96 max-w-full animate-pulse rounded bg-slate-100 dark:bg-slate-800/60" />
      </div>
      <CardSkeleton />
      <CardSkeleton />
    </div>
  )
}
