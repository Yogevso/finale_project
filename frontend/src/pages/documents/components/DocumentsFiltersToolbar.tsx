import type { KeyboardEvent as ReactKeyboardEvent, RefObject } from 'react'
import { Search, X } from 'lucide-react'

import { DOCUMENT_INPUT_LIMITS } from '@/lib/uiInputRules'
import type { Company, DocumentStatus, DocumentVisibility } from '@/types'
import type { SavedDocumentsView } from '@/pages/documents/lib/savedViews'

type DocumentsFiltersToolbarProps = {
  isLoading: boolean
  totalDocuments: number
  isAdmin: boolean
  showDeleted: boolean
  onShowDeletedChange: (value: boolean) => void
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
  onResetFilters: () => void
  savedViews: SavedDocumentsView[]
  activeSavedViewId: number | null
  onApplySavedView: (savedViewId: number) => void
  onSaveCurrentView: () => void
  onDeleteSavedView: (savedViewId: number) => void
  companies: Company[]
  categorySuggestions: string[]
  searchSuggestions: string[]
  statusDetailsRef: RefObject<HTMLDetailsElement>
  visibilityDetailsRef: RefObject<HTMLDetailsElement>
}

export function DocumentsFiltersToolbar({
  isLoading,
  totalDocuments,
  isAdmin,
  showDeleted,
  onShowDeletedChange,
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
  onResetFilters,
  savedViews,
  activeSavedViewId,
  onApplySavedView,
  onSaveCurrentView,
  onDeleteSavedView,
  companies,
  categorySuggestions,
  searchSuggestions,
  statusDetailsRef,
  visibilityDetailsRef,
}: DocumentsFiltersToolbarProps) {
  const activeCompany = companyIdFilter ? companies.find((company) => company.id === companyIdFilter) : null
  const normalizedSearch = search.trim()
  const normalizedCategory = categoryFilter.trim()
  const hasActiveFilters =
    normalizedSearch.length > 0 ||
    statusFilter !== '' ||
    visibilityFilter !== '' ||
    normalizedCategory.length > 0 ||
    companyIdFilter !== null ||
    dateFrom !== '' ||
    dateTo !== ''
  const activeFiltersCount = [
    normalizedSearch,
    statusFilter,
    visibilityFilter,
    normalizedCategory,
    companyIdFilter !== null ? String(companyIdFilter) : '',
    dateFrom,
    dateTo,
  ].filter(Boolean).length
  const searchSuggestionValues = searchSuggestions.filter((value) => value.trim().length > 0)
  const invalidDateRange = dateFrom !== '' && dateTo !== '' && dateFrom > dateTo
  const statusLabel =
    statusFilter === 'active'
      ? 'Published'
      : statusFilter === 'approved'
        ? 'Approved'
        : statusFilter || 'All'
  const visibilityLabel = visibilityFilter || 'All'
  const activeFilterBadges = [
    normalizedSearch
      ? {
          key: 'search',
          label: `Search: ${normalizedSearch}`,
          onClear: () => onSearchChange(''),
        }
      : null,
    statusFilter
      ? {
          key: 'status',
          label: `Status: ${statusLabel}`,
          onClear: () => onStatusFilterChange(''),
        }
      : null,
    visibilityFilter
      ? {
          key: 'visibility',
          label: `Visibility: ${visibilityLabel}`,
          onClear: () => onVisibilityFilterChange(''),
        }
      : null,
    normalizedCategory
      ? {
          key: 'category',
          label: `Category: ${normalizedCategory}`,
          onClear: () => onCategoryFilterChange(''),
        }
      : null,
    companyIdFilter !== null
      ? {
          key: 'company',
          label: `Company: ${activeCompany?.name ?? 'Selected company'}`,
          onClear: () => onCompanyIdFilterChange(null),
        }
      : null,
    dateFrom
      ? {
          key: 'date-from',
          label: `From: ${dateFrom}`,
          onClear: () => onDateFromChange(''),
        }
      : null,
    dateTo
      ? {
          key: 'date-to',
          label: `To: ${dateTo}`,
          onClear: () => onDateToChange(''),
        }
      : null,
  ].filter(
    (
      value,
    ): value is {
      key: string
      label: string
      onClear: () => void
    } => value !== null,
  )

  const focusFilterMenuItem = (
    detailsRef: RefObject<HTMLDetailsElement>,
    target: 'first' | 'last' | number,
  ) => {
    const items = Array.from(
      detailsRef.current?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]') ?? [],
    )
    if (items.length === 0) {
      return
    }

    if (target === 'first') {
      items[0]?.focus()
      return
    }

    if (target === 'last') {
      items[items.length - 1]?.focus()
      return
    }

    const normalizedIndex = (target + items.length) % items.length
    items[normalizedIndex]?.focus()
  }

  const openFilterMenu = (detailsRef: RefObject<HTMLDetailsElement>, target: 'first' | 'last') => {
    detailsRef.current?.setAttribute('open', '')
    focusFilterMenuItem(detailsRef, target)
  }

  const closeFilterMenu = (detailsRef: RefObject<HTMLDetailsElement>) => {
    detailsRef.current?.removeAttribute('open')
    detailsRef.current?.querySelector<HTMLElement>('summary')?.focus()
  }

  const handleFilterSummaryKeyDown = (
    event: ReactKeyboardEvent<HTMLElement>,
    detailsRef: RefObject<HTMLDetailsElement>,
  ) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      openFilterMenu(detailsRef, 'first')
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      openFilterMenu(detailsRef, 'last')
    }
  }

  const handleFilterMenuKeyDown = (
    event: ReactKeyboardEvent<HTMLDivElement>,
    detailsRef: RefObject<HTMLDetailsElement>,
  ) => {
    const items = Array.from(
      detailsRef.current?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]') ?? [],
    )
    if (items.length === 0) {
      return
    }

    const currentIndex = items.findIndex((item) => item === document.activeElement)

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        focusFilterMenuItem(detailsRef, currentIndex >= 0 ? currentIndex + 1 : 0)
        break
      case 'ArrowUp':
        event.preventDefault()
        focusFilterMenuItem(detailsRef, currentIndex >= 0 ? currentIndex - 1 : items.length - 1)
        break
      case 'Home':
        event.preventDefault()
        focusFilterMenuItem(detailsRef, 'first')
        break
      case 'End':
        event.preventDefault()
        focusFilterMenuItem(detailsRef, 'last')
        break
      case 'Escape':
        event.preventDefault()
        closeFilterMenu(detailsRef)
        break
      default:
        break
    }
  }

  return (
    <div
      className="admin-sticky-toolbar space-y-4"
      data-testid="documents-filters-toolbar"
      data-tour="documents-filter-panel"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="inline-flex items-center gap-2 text-sm text-slate-600">
          <span className="admin-summary-badge">
            {isLoading
              ? 'Loading...'
              : hasActiveFilters
                ? `${totalDocuments} matching`
                : `${totalDocuments} total`}
          </span>
          {hasActiveFilters ? (
            <span className="text-xs font-medium text-slate-500">
              {activeFiltersCount} active filter{activeFiltersCount === 1 ? '' : 's'}
            </span>
          ) : null}
          {showDeleted ? (
            <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">
              Recovery window
            </span>
          ) : null}
        </div>
        <div className="flex flex-col gap-2 lg:items-end">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                data-tour="documents-search-bar"
                type="text"
                placeholder="Search title or number"
                value={search}
                list={searchSuggestionValues.length > 0 ? 'documents-search-suggestions' : undefined}
                onChange={(event) => onSearchChange(event.target.value)}
                className="input-field pl-9 pr-10"
                aria-label="Search documents"
                maxLength={DOCUMENT_INPUT_LIMITS.filterSearch}
              />
              {normalizedSearch ? (
                <button
                  type="button"
                  onClick={() => onSearchChange('')}
                  className="absolute right-2 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
                  aria-label="Clear search"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : null}
              {searchSuggestionValues.length > 0 ? (
                <datalist id="documents-search-suggestions">
                  {searchSuggestionValues.map((value) => (
                    <option key={value} value={value} />
                  ))}
                </datalist>
              ) : null}
            </div>
            <input
              type="text"
              placeholder="Category"
              value={categoryFilter}
              list={categorySuggestions.length > 0 ? 'documents-category-suggestions' : undefined}
              onChange={(event) => onCategoryFilterChange(event.target.value)}
              className="input-field w-full sm:w-44"
              aria-label="Filter by category"
              maxLength={DOCUMENT_INPUT_LIMITS.filterCategory}
            />
            {categorySuggestions.length > 0 ? (
              <datalist id="documents-category-suggestions">
                {categorySuggestions.map((value) => (
                  <option key={value} value={value} />
                ))}
              </datalist>
            ) : null}
            <select
              value={companyIdFilter ?? ''}
              onChange={(event) =>
                onCompanyIdFilterChange(event.target.value ? Number(event.target.value) : null)
              }
              className="select-field w-full sm:w-44"
              aria-label="Filter by company"
            >
              <option value="">All companies</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
            {isAdmin ? (
              <button
                type="button"
                onClick={() => onShowDeletedChange(!showDeleted)}
                className={`btn-secondary whitespace-nowrap ${showDeleted ? 'border-rose-300 text-rose-700' : ''}`}
              >
                {showDeleted ? 'Back to documents' : 'Recovery window'}
              </button>
            ) : null}
          </div>

          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-end">
            <div className="flex flex-wrap gap-2">
              <details ref={statusDetailsRef} className="relative">
                <summary
                  className="list-none cursor-pointer whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                  aria-haspopup="menu"
                  aria-label="Filter by status"
                  onKeyDown={(event) => handleFilterSummaryKeyDown(event, statusDetailsRef)}
                >
                  Status: {statusLabel}
                </summary>
                <div
                  role="menu"
                  tabIndex={-1}
                  aria-label="Status filter options"
                  className="absolute right-0 z-10 mt-2 w-44 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
                  onKeyDown={(event) => handleFilterMenuKeyDown(event, statusDetailsRef)}
                >
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
                      role="menuitemradio"
                      aria-checked={statusFilter === item.value}
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
                <summary
                  className="list-none cursor-pointer whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                  aria-haspopup="menu"
                  aria-label="Filter by visibility"
                  onKeyDown={(event) => handleFilterSummaryKeyDown(event, visibilityDetailsRef)}
                >
                  Visibility: {visibilityLabel}
                </summary>
                <div
                  role="menu"
                  tabIndex={-1}
                  aria-label="Visibility filter options"
                  className="absolute right-0 z-10 mt-2 w-40 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
                  onKeyDown={(event) => handleFilterMenuKeyDown(event, visibilityDetailsRef)}
                >
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
                      role="menuitemradio"
                      aria-checked={visibilityFilter === item.value}
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
                max={dateTo || undefined}
                className={`input-field w-full sm:w-40 ${invalidDateRange ? 'border-rose-300 text-rose-700' : ''}`}
                aria-label="Created after"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(event) => onDateToChange(event.target.value)}
                min={dateFrom || undefined}
                className={`input-field w-full sm:w-40 ${invalidDateRange ? 'border-rose-300 text-rose-700' : ''}`}
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
                aria-label="Apply a saved documents view"
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

      {invalidDateRange ? (
        <p className="helper-copy text-rose-700">Created after must be on or before created before.</p>
      ) : null}

      {hasActiveFilters ? (
        <div className="flex flex-col gap-2 border-t border-slate-200/80 pt-3 md:flex-row md:items-start md:justify-between">
          <div className="flex flex-wrap items-center gap-2" aria-label="Active filters">
            {activeFilterBadges.map((filter) => (
              <button
                key={filter.key}
                type="button"
                onClick={filter.onClear}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
                aria-label={`Remove ${filter.label}`}
              >
                <span>{filter.label}</span>
                <X className="h-3.5 w-3.5 text-slate-400" />
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={onResetFilters}
            className="btn-ghost self-start whitespace-nowrap text-sm text-slate-600 hover:text-slate-900"
          >
            Clear all filters
          </button>
        </div>
      ) : null}
    </div>
  )
}
