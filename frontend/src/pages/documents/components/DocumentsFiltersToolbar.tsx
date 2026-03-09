import type { RefObject } from 'react'
import { Search } from 'lucide-react'

import type { Company, DocumentStatus, DocumentVisibility } from '@/types'
import type { SavedDocumentsView } from '@/pages/documents/lib/savedViews'

type DocumentsFiltersToolbarProps = {
  isLoading: boolean
  totalDocuments: number
  search: string
  onSearchChange: (value: string) => void
  statusFilter: DocumentStatus | ''
  onStatusFilterChange: (value: DocumentStatus | '') => void
  visibilityFilter: DocumentVisibility | ''
  onVisibilityFilterChange: (value: DocumentVisibility | '') => void
  categoryFilter: string
  onCategoryFilterChange: (value: string) => void
  companyIdFilter: number | null
  onCompanyIdFilterChange: (value: number | null) => void
  dateFrom: string
  onDateFromChange: (value: string) => void
  dateTo: string
  onDateToChange: (value: string) => void
  savedViews: SavedDocumentsView[]
  activeSavedViewId: number | null
  onApplySavedView: (savedViewId: number) => void
  onSaveCurrentView: () => void
  onDeleteSavedView: (savedViewId: number) => void
  companies: Company[]
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
  categoryFilter,
  onCategoryFilterChange,
  companyIdFilter,
  onCompanyIdFilterChange,
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
  savedViews,
  activeSavedViewId,
  onApplySavedView,
  onSaveCurrentView,
  onDeleteSavedView,
  companies,
  statusDetailsRef,
  visibilityDetailsRef,
}: DocumentsFiltersToolbarProps) {
  return (
    <div className="admin-sticky-toolbar space-y-4" data-tour="documents-filter-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="inline-flex items-center gap-2 text-sm text-slate-600">
          <span className="admin-summary-badge">{isLoading ? 'Loading...' : `${totalDocuments} total`}</span>
        </div>
        <div className="flex flex-col gap-2 lg:items-end">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                data-tour="documents-search-bar"
                type="text"
                placeholder="Search documents..."
                value={search}
                onChange={(event) => onSearchChange(event.target.value)}
                className="input-field pl-9"
              />
            </div>
            <input
              type="text"
              placeholder="Category"
              value={categoryFilter}
              onChange={(event) => onCategoryFilterChange(event.target.value)}
              className="input-field w-full sm:w-44"
            />
            <select
              value={companyIdFilter ?? ''}
              onChange={(event) =>
                onCompanyIdFilterChange(event.target.value ? Number(event.target.value) : null)
              }
              className="select-field w-full sm:w-44"
            >
              <option value="">All companies</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-end">
            <div className="flex flex-wrap gap-2">
              <details ref={statusDetailsRef} className="relative">
                <summary className="list-none cursor-pointer whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50">
                  Status:{' '}
                  {statusFilter === 'active'
                    ? 'Published'
                    : statusFilter === 'approved'
                      ? 'Approved'
                      : statusFilter || 'All'}
                </summary>
                <div className="absolute right-0 z-10 mt-2 w-44 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
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
                      className={`w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 ${
                        statusFilter === item.value ? 'bg-slate-100 text-slate-900' : 'text-slate-600'
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </details>

              <details ref={visibilityDetailsRef} className="relative">
                <summary className="list-none cursor-pointer whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50">
                  Visibility: {visibilityFilter || 'All'}
                </summary>
                <div className="absolute right-0 z-10 mt-2 w-40 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
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
                      className={`w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 ${
                        visibilityFilter === item.value ? 'bg-slate-100 text-slate-900' : 'text-slate-600'
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </details>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => onDateFromChange(event.target.value)}
                className="input-field w-full sm:w-40"
                aria-label="Created after"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(event) => onDateToChange(event.target.value)}
                className="input-field w-full sm:w-40"
                aria-label="Created before"
              />
              <select
                value={activeSavedViewId ?? ''}
                onChange={(event) => {
                  const nextValue = event.target.value ? Number(event.target.value) : null
                  if (nextValue) {
                    onApplySavedView(nextValue)
                  }
                }}
                className="select-field w-full sm:w-52"
              >
                <option value="">Saved views</option>
                {savedViews.map((savedView) => (
                  <option key={savedView.id} value={savedView.id}>
                    {savedView.name}
                  </option>
                ))}
              </select>
              <button type="button" onClick={onSaveCurrentView} className="btn-secondary whitespace-nowrap">
                Save view
              </button>
              {activeSavedViewId ? (
                <button
                  type="button"
                  onClick={() => onDeleteSavedView(activeSavedViewId)}
                  className="btn-ghost whitespace-nowrap text-rose-600"
                >
                  Delete view
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
