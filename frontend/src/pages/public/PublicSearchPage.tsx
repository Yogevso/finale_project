import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, FileText, ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react'
import { useState, useEffect, type ReactNode } from 'react'
import { publicApi } from '@/lib/publicApi'

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
  const parts = text.split(regex)
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-amber-200">{part}</mark>
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
  })

  // Fetch search results
  const { data: results, isLoading, isFetching } = useQuery({
    queryKey: ['public-search', { q: query, page, category }],
    queryFn: () => publicApi.search({ q: query, page, page_size: 20, category }),
    enabled: query.length >= 2,
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
    <div className="min-h-screen bg-slate-50">
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <Link
            to="/docs"
            className="inline-flex items-center gap-2 text-sky-100/80 hover:text-white mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to docs
          </Link>
          <h1 className="text-3xl md:text-4xl font-display font-bold mb-3">Search Documents</h1>
          <p className="text-sky-100 max-w-2xl">
            Search across approved documentation, release notes, and technical guides.
          </p>

          <form onSubmit={handleSearch} className="mt-6">
            <div className="relative">
              <input
                type="text"
                placeholder="Search public documents..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full px-6 py-4 pl-14 rounded-2xl text-lg text-slate-900 focus:outline-none focus:ring-4 focus:ring-sky-300/40"
              />
              <Search className="absolute left-5 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
              <button
                type="submit"
                disabled={searchInput.length < 2}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-sky-600 text-white px-6 py-2 rounded-xl hover:bg-sky-700 disabled:bg-slate-300 disabled:cursor-not-allowed font-medium"
              >
                Search
              </button>
            </div>
            {searchInput.length > 0 && searchInput.length < 2 && (
              <p className="text-sm text-sky-200/80 mt-2">Enter at least 2 characters to search</p>
            )}
          </form>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-4 py-8">
        {/* Category Filter */}
        {categories?.items && categories.items.length > 0 && query && (
          <div className="mb-6 flex flex-wrap gap-2">
            <button
              onClick={() => handleCategoryChange(null)}
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                !category
                  ? 'bg-sky-500 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All
            </button>
            {categories.items.map((cat) => (
              <button
                key={cat.category}
                onClick={() => handleCategoryChange(cat.category)}
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  category === cat.category
                    ? 'bg-sky-500 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat.category}
              </button>
            ))}
          </div>
        )}

        {/* Results */}
        {!query ? (
          <div className="text-center py-16 text-slate-500">
            <Search className="h-16 w-16 mx-auto mb-4 text-slate-300" />
            <p className="text-lg">Enter a search term to find documents</p>
          </div>
        ) : isLoading || isFetching ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="rounded-2xl border border-slate-100 bg-white p-5">
                <div className="flex items-start gap-4">
                  <div className="h-6 w-6 rounded bg-slate-200 animate-pulse flex-shrink-0 mt-1" />
                  <div className="flex-1 space-y-2">
                    <div className="h-5 w-2/3 rounded bg-slate-200 animate-pulse" />
                    <div className="h-3 w-1/4 rounded bg-slate-100 animate-pulse" />
                    <div className="h-4 w-full rounded bg-slate-100 animate-pulse" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : results?.items && results.items.length > 0 ? (
          <>
            <div className="text-sm text-slate-500 mb-4">
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
                    <FileText className="h-6 w-6 text-sky-500 flex-shrink-0 mt-1" />
                    <div className="flex-1 min-w-0">
                      <h3 
                        className="font-display font-semibold text-slate-900 group-hover:text-sky-600 mb-1"
                      >
                        <HighlightText text={item.title} query={query} />
                      </h3>
                      <p className="text-xs text-slate-400 mb-2">{item.document_number}</p>
                      {item.snippet && (
                        <p 
                          className="text-sm text-slate-600 line-clamp-2"
                        >
                          <HighlightText text={item.snippet} query={query} />
                        </p>
                      )}
                      {item.category && (
                        <span className="inline-block mt-2 pill bg-slate-100 text-slate-600 border-slate-200">
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
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page <= 1}
                  className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="text-sm text-slate-600">
                  Page {page} of {Math.ceil(results.total / results.page_size)}
                </span>
                <button
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
          <div className="text-center py-16">
            <Search className="h-16 w-16 mx-auto mb-4 text-slate-300" />
            <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No results found</h3>
            <p className="text-slate-500">
              No documents match "{query}". Try a different search term.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
