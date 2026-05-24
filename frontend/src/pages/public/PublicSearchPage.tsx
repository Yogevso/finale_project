import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, FileText, ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react'
import { useState, useEffect, type ReactNode } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { CardSkeleton } from '@/components/skeletons'
import { publicApi } from '@/lib/publicApi'
import { audienceSensitiveQueryOptions } from '@/lib/queryFreshness'

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * AD-008: Safe text highlighting using React nodes instead of dangerouslySetInnerHTML.
 * Splits `text` on matches of `query` and wraps matches in <mark>.
 */
function HighlightText({ text, query: q }: { text: string; query: string }): ReactNode {
  if (!q || !text) return <>{text}</>
  const escaped = escapeRegExp(q)
  if (!escaped) return <>{text}</>
  const regex = new RegExp(`(${escaped})`, 'gi')
  const matchRegex = new RegExp(`^${escaped}$`, 'i')
  const parts = text.split(regex)
  return (
    <>
      {parts.map((part, i) =>
        matchRegex.test(part) ? (
          <mark key={i} className="rounded-sm bg-amber-200 px-0.5">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}

export default function PublicSearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchInput, setSearchInput] = useState(searchParams.get('q') || '')
  
  const query = searchParams.get('q') || ''
  const page = parseInt(searchParams.get('page') || '1')
  const category = searchParams.get('category') || undefined

  // Fetch categories for filter
  const { data: categories } = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
    ...audienceSensitiveQueryOptions,
  })

  // Fetch search results
  const {
    data: results,
    isLoading,
    isFetching,
    isError: resultsError,
    refetch: refetchResults,
  } = useQuery({
    queryKey: ['public-search', { q: query, page, category }],
    queryFn: () => publicApi.search({ q: query, page, page_size: 20, category }),
    enabled: query.length >= 2,
    ...audienceSensitiveQueryOptions,
  })

  // Update search input when URL changes
  useEffect(() => {
    setSearchInput(searchParams.get('q') || '')
  }, [searchParams])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchInput.trim().length >= 2) {
      const params = new URLSearchParams()
      params.set('q', searchInput.trim())
      if (category) params.set('category', category)
      setSearchParams(params)
    }
  }

  const handleCategoryChange = (cat: string | null) => {
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

  // AD-008: highlight logic moved to HighlightText component (safe)

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <section className="bg-gradient-to-l from-blue-700 via-blue-600 to-blue-500 text-white">
        <div className="content-shell py-12">
          <Link
            to="/docs"
            className="inline-flex items-center gap-2 text-blue-100/80 hover:text-white mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to docs
          </Link>
          <h1 className="text-3xl md:text-4xl font-display font-bold mb-3">Search Documents</h1>
          <p className="text-blue-100 max-w-2xl">
            Search across approved documentation, release notes, and technical guides.
          </p>

          <form onSubmit={handleSearch} className="mt-6">
            <div className="relative">
              <input
                type="text"
                placeholder="Search public documents..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full rounded-2xl px-6 py-4 pl-14 text-lg text-slate-900 focus:outline-none focus:ring-4 focus:ring-blue-300/40 dark:bg-slate-950 dark:text-slate-100"
              />
              <Search className="absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
              <button
                type="submit"
                disabled={searchInput.length < 2}
                className="btn-primary table-action-btn absolute right-3 top-1/2 -translate-y-1/2 disabled:bg-slate-300 disabled:hover:scale-100"
              >
                Search
              </button>
            </div>
            {searchInput.length > 0 && searchInput.length < 2 && (
              <p className="helper-copy mt-2 text-blue-200/80">Enter at least 2 characters to search</p>
            )}
          </form>
        </div>
      </section>

      <section className="content-shell max-w-4xl py-8">
        {/* Category Filter */}
        {categories?.items && categories.items.length > 0 && query && (
          <div className="mb-6 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleCategoryChange(null)}
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                !category
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              All
            </button>
            {categories.items.map((cat) => (
              <button
                key={cat.category}
                type="button"
                onClick={() => handleCategoryChange(cat.category)}
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  category === cat.category
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {cat.category}
              </button>
            ))}
          </div>
        )}

        {/* Results */}
        {!query ? (
          <EmptyState
            icon={<Search className="h-8 w-8" aria-hidden="true" />}
            title="Search the library"
            description="Enter at least two characters to find documents, release notes, and guides."
          />
        ) : isLoading || isFetching ? (
          <CardSkeleton count={5} className="grid-cols-1" />
        ) : resultsError ? (
          <ErrorState
            title="Unable to load search results"
            message="The public search index could not be queried right now."
            onRetry={() => {
              void refetchResults()
            }}
          />
        ) : results?.items && results.items.length > 0 ? (
          <>
            <div className="body-copy mb-4">
              Found {results.total} results for "<strong>{query}</strong>"
            </div>

            <div className="space-y-4">
              {results.items.map((item) => (
                <Link
                  key={item.id}
                  to={`/doc/${item.id}?fullscreen=1`}
                  className="block surface-card-hover rounded-2xl p-5 group"
                >
                  <div className="flex items-start gap-4">
                    <FileText className="h-6 w-6 text-blue-500 flex-shrink-0 mt-1" />
                    <div className="flex-1 min-w-0">
                      <h3 className="card-title mb-1 group-hover:text-blue-600">
                        <HighlightText text={item.title} query={query} />
                      </h3>
                      <p className="helper-copy mb-2">{item.document_number}</p>
                      {item.snippet && (
                        <p className="body-copy line-clamp-2">
                          <HighlightText text={item.snippet} query={query} />
                        </p>
                      )}
                      {item.category && (
                        <span className="mt-2 inline-block pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {item.category}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            {results.total > results.page_size && (
              <div className="mt-8 flex justify-center items-center gap-4">
                <button
                  type="button"
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page <= 1}
                  className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="body-copy">
                  Page {page} of {Math.ceil(results.total / results.page_size)}
                </span>
                <button
                  type="button"
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page >= Math.ceil(results.total / results.page_size)}
                  className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            )}
          </>
        ) : (
          <EmptyState
            icon={<Search className="h-8 w-8" aria-hidden="true" />}
            title="No results found"
            description={`No documents match "${query}". Try a different search term or category.`}
          />
        )}
      </section>
    </div>
  )
}
