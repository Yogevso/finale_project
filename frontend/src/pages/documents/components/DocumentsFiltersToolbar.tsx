import type { RefObject } from 'react'

import type { DocumentStatus, DocumentVisibility } from '@/types'

type DocumentsFiltersToolbarProps = {
  isLoading: boolean
  totalDocuments: number
  search: string
  onSearchChange: (value: string) => void
  statusFilter: DocumentStatus | ''
  onStatusFilterChange: (value: DocumentStatus | '') => void
  visibilityFilter: DocumentVisibility | ''
  onVisibilityFilterChange: (value: DocumentVisibility | '') => void
  statusDetailsRef: RefObject<HTMLDetailsElement>
  visibilityDetailsRef: RefObject<HTMLDetailsElement>
}

export function DocumentsFiltersToolbar({
  isLoading,
  totalDocuments,
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  visibilityFilter,
  onVisibilityFilterChange,
  statusDetailsRef,
  visibilityDetailsRef,
}: DocumentsFiltersToolbarProps) {
  return (
    <div className="admin-sticky-toolbar" data-tour="documents-filter-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="inline-flex items-center gap-2 text-sm text-slate-600">
          <span className="admin-summary-badge">
            {isLoading ? 'Loading...' : `${totalDocuments} total`}
          </span>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
          <div className="relative w-full sm:w-72">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
            <input
              data-tour="documents-search-bar"
              type="text"
              placeholder="Search documents..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="input-field pl-9"
            />
          </div>
          <div className="flex flex-wrap gap-2 sm:justify-end">
            <details ref={statusDetailsRef} className="relative">
              <summary className="list-none cursor-pointer whitespace-nowrap px-3 py-2 rounded-full border border-slate-200 bg-white text-sm text-slate-600 hover:bg-slate-50">
                Status:{' '}
                {statusFilter === 'active'
                  ? 'Published'
                  : statusFilter === 'approved'
                    ? 'Approved'
                    : statusFilter || 'All'}
              </summary>
              <div className="absolute right-0 mt-2 w-44 rounded-xl border border-slate-200 bg-white shadow-lg p-2 z-10">
                {[
                  { label: 'All', value: '' },
                  { label: 'Draft', value: 'draft' },
                  { label: 'Pending Review', value: 'pending_review' },
                  { label: 'Approved', value: 'approved' },
                  { label: 'Published', value: 'active' },
                  { label: 'Archived', value: 'archived' },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => {
                      onStatusFilterChange(item.value as DocumentStatus | '')
                      statusDetailsRef.current?.removeAttribute('open')
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-slate-100 ${
                      statusFilter === item.value
                        ? 'bg-slate-100 text-slate-900'
                        : 'text-slate-600'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </details>

            <details ref={visibilityDetailsRef} className="relative">
              <summary className="list-none cursor-pointer whitespace-nowrap px-3 py-2 rounded-full border border-slate-200 bg-white text-sm text-slate-600 hover:bg-slate-50">
                Visibility: {visibilityFilter || 'All'}
              </summary>
              <div className="absolute right-0 mt-2 w-40 rounded-xl border border-slate-200 bg-white shadow-lg p-2 z-10">
                {[
                  { label: 'All', value: '' },
                  { label: 'Public', value: 'public' },
                  { label: 'Internal', value: 'internal' },
                  { label: 'Company', value: 'company' },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => {
                      onVisibilityFilterChange(item.value as DocumentVisibility | '')
                      visibilityDetailsRef.current?.removeAttribute('open')
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-slate-100 ${
                      visibilityFilter === item.value
                        ? 'bg-slate-100 text-slate-900'
                        : 'text-slate-600'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </details>
          </div>
        </div>
      </div>
    </div>
  )
}
