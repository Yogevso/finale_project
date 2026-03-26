import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, FileText, Folder } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { CardSkeleton, ListSkeleton } from '@/components/skeletons'
import type { PublicDocumentListResponse } from '@/lib/publicApi'

import { formatPublicDate, getDocumentTags } from '../lib/catalog'

interface PublicDocumentsResultsProps {
  docs?: PublicDocumentListResponse
  isError: boolean
  isLoading: boolean
  onClearFilters?: () => void
  onPageChange: (page: number) => void
  onRetry: () => void
  page: number
  search?: string
  selectedCategory?: string
  viewMode: 'grid' | 'list'
}

export function PublicDocumentsResults({
  docs,
  isError,
  isLoading,
  onClearFilters,
  onPageChange,
  onRetry,
  page,
  search,
  selectedCategory,
  viewMode,
}: PublicDocumentsResultsProps) {
  if (isLoading) {
    return viewMode === 'grid' ? (
      <CardSkeleton count={6} className="md:grid-cols-2 xl:grid-cols-3" />
    ) : (
      <ListSkeleton rows={6} />
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="Unable to load documents"
        message="The documentation library could not be loaded right now."
        onRetry={onRetry}
      />
    )
  }

  if (docs?.items && docs.items.length > 0) {
    return (
      <>
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {docs.items.map((doc) => (
              <Link
                key={doc.id}
                to={`/doc/${doc.id}?fullscreen=1`}
                className="surface-card-hover group rounded-2xl p-6"
              >
                <div className="flex items-start gap-4">
                  <div className="rounded-xl bg-sky-100 p-3 dark:bg-sky-950/40">
                    <FileText className="h-6 w-6 text-sky-700" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="card-title truncate group-hover:text-sky-700">{doc.title}</h3>
                    <p className="helper-copy mt-1">{doc.document_number}</p>
                    <p className="body-copy mt-2 line-clamp-2">{doc.description || 'No description'}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {doc.platform ? (
                        <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {doc.platform}
                        </span>
                      ) : null}
                      {getDocumentTags(doc.tags).map((tag) => (
                        <span
                          key={tag}
                          className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between text-xs text-slate-600 dark:text-slate-500">
                  <span>{formatPublicDate(doc.created_at)}</span>
                  {doc.category ? (
                    <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                      {doc.category}
                    </span>
                  ) : null}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {docs.items.map((doc) => (
              <Link
                key={doc.id}
                to={`/doc/${doc.id}?fullscreen=1`}
                className="group block rounded-2xl p-4 surface-card-hover"
              >
                <div className="flex items-center gap-4">
                  <FileText className="h-8 w-8 flex-shrink-0 text-sky-700" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="card-title group-hover:text-sky-700">{doc.title}</h3>
                      <span className="helper-copy">{doc.document_number}</span>
                    </div>
                    <p className="body-copy truncate">{doc.description || 'No description'}</p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {doc.platform ? (
                        <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {doc.platform}
                        </span>
                      ) : null}
                      {getDocumentTags(doc.tags).map((tag) => (
                        <span
                          key={tag}
                          className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <div className="body-copy">{formatPublicDate(doc.created_at)}</div>
                    {doc.category ? (
                      <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                        {doc.category}
                      </span>
                    ) : null}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {docs.total_pages > 1 ? (
          <div className="mt-8 flex items-center justify-center gap-4">
            <button
              type="button"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="btn-ghost disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <span className="body-copy">
              Page {page} of {docs.total_pages}
            </span>
            <button
              type="button"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= docs.total_pages}
              className="btn-ghost disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Next page"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        ) : null}
      </>
    )
  }

  return (
    <EmptyState
      icon={<Folder className="h-8 w-8" aria-hidden="true" />}
      title="No documents found"
      description={
        search
          ? `No documents match "${search}".`
          : 'No approved documents are available for the current category.'
      }
      action={
        selectedCategory || search
          ? {
              label: 'Clear filters',
              onClick: () => onClearFilters?.(),
            }
          : undefined
      }
    />
  )
}
