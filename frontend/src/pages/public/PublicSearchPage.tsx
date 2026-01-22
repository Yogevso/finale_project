import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, FileText, ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react'
import { useState, useEffect } from 'react'
import { publicApi } from '@/lib/publicApi'

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

  const highlightQuery = (text: string) => {
    if (!query || !text) return text
    const regex = new RegExp(`(${query})`, 'gi')
    return text.replace(regex, '<mark class="bg-yellow-200">$1</mark>')
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Search Documents</h1>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="relative">
          <input
            type="text"
            placeholder="Search public documents..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full px-6 py-4 pl-14 border border-gray-300 rounded-xl text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <Search className="absolute left-5 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <button
            type="submit"
            disabled={searchInput.length < 2}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Search
          </button>
        </div>
        {searchInput.length > 0 && searchInput.length < 2 && (
          <p className="text-sm text-gray-500 mt-2">Enter at least 2 characters to search</p>
        )}
      </form>

      {/* Category Filter */}
      {categories?.items && categories.items.length > 0 && query && (
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => handleCategoryChange(null)}
            className={`px-3 py-1 rounded-full text-sm ${
              !category
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          {categories.items.map((cat) => (
            <button
              key={cat.category}
              onClick={() => handleCategoryChange(cat.category)}
              className={`px-3 py-1 rounded-full text-sm ${
                category === cat.category
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {cat.category}
            </button>
          ))}
        </div>
      )}

      {/* Results */}
      {!query ? (
        <div className="text-center py-16 text-gray-500">
          <Search className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <p className="text-lg">Enter a search term to find documents</p>
        </div>
      ) : isLoading || isFetching ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : results?.items && results.items.length > 0 ? (
        <>
          <div className="text-sm text-gray-500 mb-4">
            Found {results.total} results for "<strong>{query}</strong>"
          </div>

          <div className="space-y-4">
            {results.items.map((item) => (
              <Link
                key={item.id}
                to={`/doc/${item.id}`}
                className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-5 group"
              >
                <div className="flex items-start gap-4">
                  <FileText className="h-6 w-6 text-blue-500 flex-shrink-0 mt-1" />
                  <div className="flex-1 min-w-0">
                    <h3 
                      className="font-semibold text-gray-900 group-hover:text-blue-600 mb-1"
                      dangerouslySetInnerHTML={{ __html: highlightQuery(item.title) }}
                    />
                    <p className="text-xs text-gray-400 mb-2">{item.document_number}</p>
                    {item.snippet && (
                      <p 
                        className="text-sm text-gray-600 line-clamp-2"
                        dangerouslySetInnerHTML={{ __html: highlightQuery(item.snippet) }}
                      />
                    )}
                    {item.category && (
                      <span className="inline-block mt-2 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
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
                className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="text-sm text-gray-600">
                Page {page} of {Math.ceil(results.total / results.page_size)}
              </span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= Math.ceil(results.total / results.page_size)}
                className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-16">
          <Search className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
          <p className="text-gray-500">
            No documents match "{query}". Try a different search term.
          </p>
        </div>
      )}
    </div>
  )
}
