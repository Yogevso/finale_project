import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, FileText, Search } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { CardSkeleton } from '@/components/skeletons'
import { audienceSensitiveQueryOptions, fetchFresh } from '@/lib/queryFreshness'
import type { Document, DocumentListResponse } from '@/types'

export default function ViewerHomePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '')

  const page = parseInt(searchParams.get('page') || '1')
  const search = searchParams.get('search') || ''
  const category = searchParams.get('category') || ''

  const {
    data,
    isLoading,
    isError: documentsError,
    refetch: refetchDocuments,
  } = useQuery<DocumentListResponse>({
    queryKey: ['viewer-documents', page, search, category],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('page', page.toString())
      params.set('page_size', '12')
      if (search) params.set('search', search)
      if (category) params.set('category', category)

      const response = await fetchFresh(`/api/v1/viewer/documents?${params}`)
      if (!response.ok) throw new Error('Failed to fetch documents')
      return response.json() as Promise<DocumentListResponse>
    },
    ...audienceSensitiveQueryOptions,
  })

  const { data: categories = [] } = useQuery<string[]>({
    queryKey: ['viewer-categories'],
    queryFn: async () => {
      const response = await fetchFresh('/api/v1/viewer/documents/categories')
      if (!response.ok) throw new Error('Failed to fetch categories')
      return response.json() as Promise<string[]>
    },
    ...audienceSensitiveQueryOptions,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (searchInput) {
      params.set('search', searchInput)
    } else {
      params.delete('search')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const handleCategoryChange = (cat: string) => {
    const params = new URLSearchParams(searchParams)
    if (cat) {
      params.set('category', cat)
    } else {
      params.delete('category')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', newPage.toString())
    setSearchParams(params)
  }

  const documents: Document[] = data?.items || []
  const totalPages = data?.total_pages || 1

  return (
    <div className="min-h-screen animate-fade-in bg-gradient-to-br from-slate-50 to-sky-50 dark:from-slate-950 dark:to-slate-900">
      <header className="border-b border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="content-shell py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-display font-bold text-slate-900 dark:text-slate-100">
                Documentation Platform
              </h1>
              <p className="body-copy mt-1">Browse our published documents</p>
            </div>
            <Link to="/login" className="btn-secondary table-action-btn">
              Staff Login
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="content-shell py-8">
        <div className="surface-card mb-8 rounded-2xl p-6">
          <form onSubmit={handleSearch} className="flex flex-col gap-4 md:flex-row">
            <div className="flex-1">
              <div className="relative">
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search documents..."
                  className="input-field w-full pl-10"
                />
                <Search className="absolute left-3 top-3.5 h-5 w-5 text-slate-400 dark:text-slate-500" />
              </div>
            </div>

            <select
              value={category}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="select-field"
            >
              <option value="">All Categories</option>
              {categories.map((cat: string) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <button type="submit" className="btn-primary">
              Search
            </button>
          </form>

          {search || category ? (
            <div className="mt-4 flex items-center gap-2">
              <span className="helper-copy">Filters:</span>
              {search ? (
                <span className="pill flex items-center gap-1 border-sky-200 bg-sky-100 text-sky-700 dark:border-sky-900 dark:bg-sky-950/50 dark:text-sky-200">
                  "{search}"
                  <button
                    type="button"
                    onClick={() => {
                      setSearchInput('')
                      const params = new URLSearchParams(searchParams)
                      params.delete('search')
                      setSearchParams(params)
                    }}
                    className="hover:text-sky-900 dark:hover:text-sky-100"
                    aria-label={`Remove search filter ${search}`}
                  >
                    x
                  </button>
                </span>
              ) : null}
              {category ? (
                <span className="pill flex items-center gap-1 border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200">
                  {category}
                  <button
                    type="button"
                    onClick={() => handleCategoryChange('')}
                    className="hover:text-emerald-900 dark:hover:text-emerald-100"
                    aria-label={`Remove category filter ${category}`}
                  >
                    x
                  </button>
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        {isLoading ? (
          <CardSkeleton count={6} className="md:grid-cols-2 xl:grid-cols-3" />
        ) : documentsError ? (
          <ErrorState
            title="Unable to load published documents"
            message="The viewer document library is unavailable right now."
            onRetry={() => {
              void refetchDocuments()
            }}
          />
        ) : documents.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-8 w-8" aria-hidden="true" />}
            title="No documents found"
            description={
              search || category
                ? 'Try adjusting your search or filters.'
                : 'No published documents are available yet.'
            }
            action={
              search || category
                ? {
                    label: 'Clear filters',
                    onClick: () => {
                      setSearchInput('')
                      setSearchParams({})
                    },
                  }
                : undefined
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {documents.map((doc) => (
              <Link
                key={doc.id}
                to={`/viewer/documents/${doc.id}?fullscreen=1`}
                className="group surface-card-hover rounded-2xl p-6"
              >
                <div className="mb-3 flex items-start justify-between">
                  <span className="pill border-sky-200 bg-sky-100 text-sky-700 dark:border-sky-900 dark:bg-sky-950/50 dark:text-sky-200">
                    {doc.category || 'General'}
                  </span>
                  <span className="helper-copy">{doc.document_number}</span>
                </div>

                <h2 className="card-title mb-2 line-clamp-2 transition-colors group-hover:text-sky-600">
                  {doc.title}
                </h2>

                {doc.description ? (
                  <p className="body-copy mb-4 line-clamp-3">{doc.description}</p>
                ) : null}

                <div className="mt-auto flex items-center justify-between border-t border-slate-200 pt-4 dark:border-slate-800">
                  <span className="helper-copy">Updated {new Date(doc.updated_at).toLocaleDateString()}</span>
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-sky-600 group-hover:underline">
                    Read more
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {totalPages > 1 ? (
          <div className="surface-card mt-8 flex items-center justify-center gap-2 rounded-2xl px-4 py-3">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1}
              className="btn-ghost table-action-btn disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
            >
              Previous
            </button>

            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                let pageNum = i + 1
                if (totalPages > 5) {
                  if (page <= 3) {
                    pageNum = i + 1
                  } else if (page >= totalPages - 2) {
                    pageNum = totalPages - 4 + i
                  } else {
                    pageNum = page - 2 + i
                  }
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`h-10 w-10 rounded-xl font-medium transition-colors ${
                      page === pageNum
                        ? 'bg-sky-600 text-white'
                        : 'border border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`}
                    type="button"
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages}
              className="btn-ghost table-action-btn disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
            >
              Next
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        ) : null}
      </main>

      <footer className="mt-16 border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
        <div className="content-shell py-8 text-center">
          <p className="body-copy">Documentation Platform | Built with React + FastAPI</p>
        </div>
      </footer>
    </div>
  )
}
