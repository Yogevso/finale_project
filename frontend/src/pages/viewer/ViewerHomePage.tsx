import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import type { Document, DocumentListResponse } from '@/types'

export default function ViewerHomePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '')
  
  const page = parseInt(searchParams.get('page') || '1')
  const search = searchParams.get('search') || ''
  const category = searchParams.get('category') || ''

  // Fetch published documents
  const { data, isLoading } = useQuery<DocumentListResponse>({
    queryKey: ['viewer-documents', page, search, category],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('page', page.toString())
      params.set('page_size', '12')
      if (search) params.set('search', search)
      if (category) params.set('category', category)
      
      const response = await fetch(`/api/v1/viewer/documents?${params}`)
      if (!response.ok) throw new Error('Failed to fetch documents')
      return response.json() as Promise<DocumentListResponse>
    },
  })

  // Fetch categories
  const { data: categories = [] } = useQuery<string[]>({
    queryKey: ['viewer-categories'],
    queryFn: async () => {
      const response = await fetch('/api/v1/viewer/documents/categories')
      if (!response.ok) throw new Error('Failed to fetch categories')
      return response.json() as Promise<string[]>
    },
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
  const totalPages = data?.pages || 1

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-display font-bold text-slate-900">📚 Documentation Platform</h1>
              <p className="text-slate-500 mt-1">Browse our published documents</p>
            </div>
            <Link
              to="/login"
              className="text-sm text-sky-600 hover:text-sky-700 font-medium"
            >
              Staff Login →
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Search & Filters */}
        <div className="surface-card rounded-2xl p-6 mb-8">
          <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search documents..."
                  className="input-field w-full pl-10"
                />
                <svg
                  className="absolute left-3 top-3.5 h-5 w-5 text-slate-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
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

            <button
              type="submit"
              className="btn-primary"
            >
              Search
            </button>
          </form>

          {(search || category) && (
            <div className="mt-4 flex items-center gap-2 text-sm">
              <span className="text-slate-500">Filters:</span>
              {search && (
                <span className="pill bg-sky-100 text-sky-700 flex items-center gap-1">
                  "{search}"
                  <button
                    onClick={() => {
                      setSearchInput('')
                      const params = new URLSearchParams(searchParams)
                      params.delete('search')
                      setSearchParams(params)
                    }}
                    className="hover:text-sky-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {category && (
                <span className="pill bg-emerald-100 text-emerald-700 flex items-center gap-1">
                  {category}
                  <button
                    onClick={() => handleCategoryChange('')}
                    className="hover:text-emerald-900"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Documents Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="surface-card rounded-2xl p-6 animate-pulse"
              >
                <div className="h-6 bg-slate-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-slate-100 rounded w-full mb-2"></div>
                <div className="h-4 bg-slate-100 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-16 surface-card rounded-2xl">
            <div className="text-6xl mb-4">📄</div>
            <h2 className="text-xl font-display font-semibold text-slate-900 mb-2">
              No Documents Found
            </h2>
            <p className="text-slate-500">
              {search || category
                ? 'Try adjusting your search or filters'
                : 'No published documents available yet'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {documents.map((doc) => (
              <Link
                key={doc.id}
                to={`/viewer/documents/${doc.id}?fullscreen=1`}
                className="surface-card-hover rounded-2xl p-6 group"
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="pill bg-sky-100 text-sky-700">
                    {doc.category || 'General'}
                  </span>
                  <span className="text-xs text-slate-400">
                    {doc.document_number}
                  </span>
                </div>
                
                <h2 className="text-lg font-display font-semibold text-slate-900 mb-2 group-hover:text-sky-600 transition-colors line-clamp-2">
                  {doc.title}
                </h2>
                
                {doc.description && (
                  <p className="text-slate-600 text-sm line-clamp-3 mb-4">
                    {doc.description}
                  </p>
                )}

                <div className="flex items-center justify-between text-xs text-slate-400 mt-auto pt-4 border-t border-slate-200">
                  <span>
                    Updated {new Date(doc.updated_at).toLocaleDateString()}
                  </span>
                  <span className="text-sky-600 group-hover:underline">
                    Read more →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-8">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1}
              className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>
            
            <div className="flex items-center gap-1">
              {[...Array(Math.min(5, totalPages))].map((_, i) => {
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
                    className={`w-10 h-10 rounded-xl font-medium transition-colors ${
                      page === pageNum
                        ? 'bg-sky-600 text-white'
                        : 'border border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages}
              className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next →
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-8 text-center text-slate-500 text-sm">
          <p>Documentation Platform • Built with React + FastAPI</p>
        </div>
      </footer>
    </div>
  )
}
