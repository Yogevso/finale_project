import { Link } from 'react-router-dom'
import { Grid, List } from 'lucide-react'

interface PublicDocumentsToolbarProps {
  activeCategory?: string
  resultCount: number
  search?: string
  viewMode: 'grid' | 'list'
  onClearAllFilters: () => void
  onClearCategory: () => void
  onClearSearch: () => void
  onViewModeChange: (value: 'grid' | 'list') => void
}

export function PublicDocumentsToolbar({
  activeCategory,
  resultCount,
  search,
  viewMode,
  onClearAllFilters,
  onClearCategory,
  onClearSearch,
  onViewModeChange,
}: PublicDocumentsToolbarProps) {
  return (
    <div className="surface-card mb-6 rounded-2xl px-4 py-3">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="body-copy">
          <span className="font-semibold text-slate-900 dark:text-slate-100">{resultCount}</span>{' '}
          documents found
        </div>
        <div className="flex items-center gap-2">
          <Link to="/platforms" className="btn-secondary table-action-btn">
            Explore Platforms
          </Link>
          <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900">
            <button
              type="button"
              onClick={() => onViewModeChange('grid')}
              className={`rounded-lg p-2 ${
                viewMode === 'grid'
                  ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-500 dark:hover:bg-slate-800'
              }`}
              aria-label="Grid view"
            >
              <Grid className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => onViewModeChange('list')}
              className={`rounded-lg p-2 ${
                viewMode === 'list'
                  ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-500 dark:hover:bg-slate-800'
              }`}
              aria-label="List view"
            >
              <List className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {activeCategory || search ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {activeCategory ? (
            <button
              type="button"
              onClick={onClearCategory}
              className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200"
            >
              Category: {activeCategory}
              <span aria-hidden>x</span>
            </button>
          ) : null}
          {search ? (
            <button
              type="button"
              onClick={onClearSearch}
              className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              Search: {search}
              <span aria-hidden>x</span>
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClearAllFilters}
            className="text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          >
            Clear all
          </button>
        </div>
      ) : null}
    </div>
  )
}
