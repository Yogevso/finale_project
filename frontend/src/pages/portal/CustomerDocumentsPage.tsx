/**
 * CustomerDocumentsPage - Document listing for customer portal with faceted sidebar filters
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileText,
  Folder,
  LayoutGrid,
  List,
  Monitor,
  Paperclip,
  Search,
  Tag,
  X,
} from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { CardSkeleton } from '@/components/skeletons'
import { audienceSensitiveQueryOptions } from '@/lib/queryFreshness'

import { portalApi } from '../../lib/portalApi'
import type { FacetItem } from '../../lib/portalApi'

export default function CustomerDocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  const page = parseInt(searchParams.get('page') || '1')
  const category = searchParams.get('category') || undefined
  const topic = searchParams.get('topic') || undefined
  const platform = searchParams.get('platform') || undefined
  const dateFrom = searchParams.get('date_from') || ''
  const dateTo = searchParams.get('date_to') || ''
  const search = searchParams.get('search') || ''

  const updateSearchParams = (updater: (params: URLSearchParams) => void) => {
    const nextParams = new URLSearchParams(searchParams)
    updater(nextParams)
    setSearchParams(nextParams)
  }

  // Fetch documents with all filters
  const {
    data: documents,
    isLoading,
    isError: isDocumentsError,
    refetch: refetchDocuments,
  } = useQuery({
    queryKey: ['portal', 'documents', { page, category, topic, platform, dateFrom, dateTo, search }],
    queryFn: () =>
      portalApi.getDocuments({
        page,
        category,
        topic,
        platform,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: search || undefined,
        per_page: 12,
      }),
    ...audienceSensitiveQueryOptions,
  })

  // Fetch facets for sidebar
  const { data: facets } = useQuery({
    queryKey: ['portal', 'facets'],
    queryFn: () => portalApi.getFacets(),
    ...audienceSensitiveQueryOptions,
  })

  const handleSearchChange = (nextSearch: string) => {
    updateSearchParams((params) => {
      const trimmed = nextSearch.trim()
      if (trimmed) {
        params.set('search', nextSearch)
      } else {
        params.delete('search')
      }
      params.delete('page')
    })
  }

  const setFilter = (key: string, value: string | null) => {
    updateSearchParams((params) => {
      if (value) {
        params.set(key, value)
      } else {
        params.delete(key)
      }
      params.delete('page')
    })
  }

  const clearAllFilters = () => {
    setSearchParams(new URLSearchParams())
  }

  const handlePageChange = (newPage: number) => {
    updateSearchParams((params) => {
      params.set('page', String(newPage))
    })
  }

  const hasActiveFilters = !!(category || topic || platform || dateFrom || dateTo || search)

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Customer Portal"
        title="Documents"
        subtitle="Browse all available documents and resources"
      />

      <div className="flex gap-6">
        {/* Sidebar Faceted Filters */}
        <aside className="hidden lg:block w-64 flex-shrink-0 space-y-4">
          {/* Search */}
          <div className="surface-card rounded-2xl p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
              <input
                type="search"
                name="search"
                value={search}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Search..."
                className="input-field pl-9 text-sm"
              />
            </div>
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearAllFilters}
            className="body-copy flex w-full items-center justify-center gap-1 font-medium text-blue-600 hover:text-blue-700"
            >
              <X className="h-3.5 w-3.5" />
              Clear all filters
            </button>
          )}

          {/* Category Facet */}
          <FacetSection
            title="Category"
            icon={<Folder className="h-4 w-4" />}
            items={facets?.categories ?? []}
            selected={category}
            onSelect={(val) => setFilter('category', val)}
          />

          {/* Topic Facet */}
          <FacetSection
            title="Topic"
            icon={<Tag className="h-4 w-4" />}
            items={facets?.topics ?? []}
            selected={topic}
            onSelect={(val) => setFilter('topic', val)}
          />

          {/* Platform Facet */}
          <FacetSection
            title="Platform"
            icon={<Monitor className="h-4 w-4" />}
            items={facets?.platforms ?? []}
            selected={platform}
            onSelect={(val) => setFilter('platform', val)}
          />

          {/* Date Range */}
          <div className="surface-card rounded-2xl p-4">
            <h3 className="card-title mb-3 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Date Range
            </h3>
            <div className="space-y-2">
              <label htmlFor="customer-docs-date-from" className="helper-copy block">From</label>
              <input
                id="customer-docs-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setFilter('date_from', e.target.value || null)}
                className="input-field text-sm"
              />
              <label htmlFor="customer-docs-date-to" className="helper-copy block">To</label>
              <input
                id="customer-docs-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setFilter('date_to', e.target.value || null)}
                className="input-field text-sm"
              />
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Mobile search + filter bar */}
          <div className="lg:hidden surface-card rounded-2xl p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                <input
                  type="search"
                  name="search"
                  value={search}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  placeholder="Search documents..."
                  className="input-field pl-10"
                />
              </div>
              <select
                value={category || ''}
                onChange={(e) => setFilter('category', e.target.value || null)}
                className="select-field"
              >
                <option value="">All Categories</option>
                {facets?.categories.map((f) => (
                  <option key={f.name} value={f.name}>
                    {f.name} ({f.count})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* View toggle + Active filters */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              {category && (
                <FilterPill label={category} onRemove={() => setFilter('category', null)} />
              )}
              {topic && (
                <FilterPill label={topic} onRemove={() => setFilter('topic', null)} />
              )}
              {platform && (
                <FilterPill label={platform} onRemove={() => setFilter('platform', null)} />
              )}
              {dateFrom && (
                <FilterPill label={`From ${dateFrom}`} onRemove={() => setFilter('date_from', null)} />
              )}
              {dateTo && (
                <FilterPill label={`Until ${dateTo}`} onRemove={() => setFilter('date_to', null)} />
              )}
              {search && (
                <FilterPill label={`"${search}"`} onRemove={() => handleSearchChange('')} />
              )}
            </div>
            <div className="flex overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => setViewMode('grid')}
                className={`p-2 ${
                  viewMode === 'grid'
                    ? 'bg-blue-100 text-blue-600 dark:bg-blue-950/50 dark:text-blue-200'
                    : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                }`}
                aria-label="Grid view"
              >
                <LayoutGrid className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('list')}
                className={`p-2 ${
                  viewMode === 'list'
                    ? 'bg-blue-100 text-blue-600 dark:bg-blue-950/50 dark:text-blue-200'
                    : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                }`}
                aria-label="List view"
              >
                <List className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Documents */}
          {isLoading ? (
            <CardSkeleton count={viewMode === 'grid' ? 6 : 4} className="xl:grid-cols-3" />
          ) : isDocumentsError ? (
            <ErrorState
              title="Documents could not be loaded"
              message="We could not fetch customer portal documents."
              onRetry={() => void refetchDocuments()}
            />
          ) : documents?.items.length === 0 ? (
            <EmptyState
              icon={<FileText className="h-8 w-8" aria-hidden="true" />}
              title="No documents found"
              description={
                hasActiveFilters
                  ? 'Try adjusting your search or filters.'
                  : 'No documents are available at this time.'
              }
              action={hasActiveFilters ? { label: 'Clear Filters', onClick: clearAllFilters } : undefined}
            />
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {documents?.items.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/portal/documents/${doc.id}?fullscreen=1`}
                  className="surface-card-hover rounded-2xl p-5"
                >
                  <div className="flex items-start">
                    <FileText className="h-10 w-10 text-blue-500 flex-shrink-0" />
                    <div className="ml-4 flex-1 min-w-0">
                      <h3 className="card-title truncate">{doc.title}</h3>
                      {doc.description && (
                        <p className="helper-copy mt-1 line-clamp-2">{doc.description}</p>
                      )}
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
                    <div className="flex items-center gap-2">
                      {doc.category && (
                        <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{doc.category}</span>
                      )}
                      {doc.has_attachments && <Paperclip className="h-4 w-4" />}
                    </div>
                    <span>v{doc.version}</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="surface-card divide-y divide-slate-100 rounded-2xl dark:divide-slate-800">
              {documents?.items.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/portal/documents/${doc.id}?fullscreen=1`}
                  className="block p-4 hover:bg-slate-50 dark:hover:bg-slate-800/70"
                >
                  <div className="flex items-center">
                    <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
                    <div className="ml-4 flex-1 min-w-0">
                      <h3 className="card-title">{doc.title}</h3>
                      {doc.description && <p className="helper-copy truncate">{doc.description}</p>}
                    </div>
                    <div className="helper-copy ml-4 flex items-center gap-3">
                      {doc.category && (
                        <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{doc.category}</span>
                      )}
                      {doc.has_attachments && <Paperclip className="h-4 w-4" />}
                      <span>v{doc.version}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* Pagination */}
          {documents && documents.total_pages > 1 && (
            <div className="flex items-center justify-between surface-card rounded-2xl px-4 py-3">
              <p className="body-copy">
                Showing {(page - 1) * 12 + 1} to {Math.min(page * 12, documents.total)} of{' '}
                {documents.total} results
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page === 1}
                  className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="body-copy px-4 py-2">
                  Page {page} of {documents.total_pages}
                </span>
                <button
                  type="button"
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page === documents.total_pages}
                  className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Next page"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function FacetSection({
  title,
  icon,
  items,
  selected,
  onSelect,
}: {
  title: string
  icon: React.ReactNode
  items: FacetItem[]
  selected: string | undefined
  onSelect: (value: string | null) => void
}) {
  if (items.length === 0) return null

  return (
    <div className="surface-card rounded-2xl p-4">
      <h3 className="card-title mb-3 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.name}>
            <button
              type="button"
              onClick={() => onSelect(selected === item.name ? null : item.name)}
              className={`w-full text-left px-2 py-1.5 rounded-lg text-sm flex items-center justify-between transition-colors ${
                selected === item.name
                  ? 'bg-blue-100 text-blue-700 font-medium dark:bg-blue-950/50 dark:text-blue-200'
                  : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              <span className="truncate">{item.name}</span>
              <span className={`ml-2 flex-shrink-0 text-xs ${selected === item.name ? 'text-blue-500 dark:text-blue-300' : 'text-slate-400 dark:text-slate-500'}`}>
                {item.count}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function FilterPill({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-700 dark:bg-blue-950/50 dark:text-blue-200">
      {label}
      <button
        type="button"
        onClick={onRemove}
        className="ml-2 hover:text-blue-900 dark:hover:text-blue-100"
        aria-label={`Remove filter ${label}`}
      >
        &times;
      </button>
    </span>
  )
}
