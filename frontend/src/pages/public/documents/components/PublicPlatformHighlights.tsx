import { Link } from 'react-router-dom'

import { formatPublicDate, type PlatformReleasePreview } from '../lib/catalog'

interface PublicPlatformHighlightsProps {
  items: PlatformReleasePreview[]
}

export function PublicPlatformHighlights({ items }: PublicPlatformHighlightsProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <div className="surface-card mb-8 rounded-3xl p-6">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-600">Latest Releases</div>
          <h2 className="page-title">Platform highlights</h2>
          <p className="body-copy mt-1">
            The newest published documents across active platforms.
          </p>
        </div>
        <Link to="/platforms" className="btn-secondary table-action-btn">
          Full platform history
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {items.map((item) => (
          <Link
            key={item.platform}
            to={item.platformId ? `/platforms/${item.platformId}` : '/platforms'}
            className="surface-muted block cursor-pointer rounded-2xl p-4 transition-shadow hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <div className="text-xs uppercase tracking-widest text-slate-600">Platform</div>
            <div className="section-title mt-1">{item.platform}</div>
            <div className="body-copy mt-3">{item.latestDoc.title}</div>
            <div className="helper-copy mt-3 flex flex-wrap items-center gap-2">
              {item.latestDoc.releaseBranch ? (
                <span className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                  {item.latestDoc.releaseBranch}
                </span>
              ) : null}
              <span className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                {item.latestDoc.versionLabel ||
                  (item.latestDoc.versionNumber ? `v${item.latestDoc.versionNumber}` : 'Version -')}
              </span>
              {item.latestDoc.publishedAt ? <span>{formatPublicDate(item.latestDoc.publishedAt)}</span> : null}
            </div>
            <div className="mt-3 font-mono text-xs text-slate-600">
              {item.latestDoc.documentNumber}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
