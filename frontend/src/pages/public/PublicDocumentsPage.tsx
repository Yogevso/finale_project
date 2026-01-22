import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Folder, ChevronLeft, ChevronRight, Grid, List, Search } from 'lucide-react'
import { useState } from 'react'
import { publicApi } from '@/lib/publicApi'

export default function PublicDocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [localSearch, setLocalSearch] = useState('')

  const page = parseInt(searchParams.get('page') || '1')
  const category = searchParams.get('category') || undefined
  const search = searchParams.get('search') || undefined

  // Fetch documents
  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['public-documents', { page, page_size: 12, category, search }],
    queryFn: () => publicApi.getDocuments({ page, page_size: 12, category, search }),
  })

  // Fetch categories for sidebar
  const { data: categories } = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
  })

  const handleCategoryClick = (cat: string | null) => {
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

  const handleLocalSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (localSearch.trim()) {
      params.set('search', localSearch)
    } else {
      params.delete('search')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Browse Documents</h1>
        <p className="text-gray-600 mt-2">
          Explore our public documentation library
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <aside className="lg:w-64 flex-shrink-0">
          {/* Search */}
          <form onSubmit={handleLocalSearch} className="mb-6">
            <div className="relative">
              <input
                type="text"
                placeholder="Search..."
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            </div>
          </form>

          {/* Categories */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Categories</h3>
            <ul className="space-y-1">
              <li>
                <button
                  onClick={() => handleCategoryClick(null)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                    !category
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  All Categories
                </button>
              </li>
              {categories?.items?.map((cat) => (
                <li key={cat.category}>
                  <button
                    onClick={() => handleCategoryClick(cat.category)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex justify-between items-center ${
                      category === cat.category
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <span className="truncate">{cat.category}</span>
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">
                      {cat.count}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1">
          {/* Toolbar */}
          <div className="flex justify-between items-center mb-6">
            <div className="text-sm text-gray-500">
              {docs?.total || 0} documents found
              {category && <span> in <strong>{category}</strong></span>}
              {search && <span> matching "<strong>{search}</strong>"</span>}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-lg ${
                  viewMode === 'grid'
                    ? 'bg-blue-100 text-blue-600'
                    : 'text-gray-400 hover:bg-gray-100'
                }`}
              >
                <Grid className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-lg ${
                  viewMode === 'list'
                    ? 'bg-blue-100 text-blue-600'
                    : 'text-gray-400 hover:bg-gray-100'
                }`}
              >
                <List className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Documents */}
          {docsLoading ? (
            <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-40 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : docs?.items && docs.items.length > 0 ? (
            <>
              {viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {docs.items.map((doc) => (
                    <Link
                      key={doc.id}
                      to={`/doc/${doc.id}`}
                      className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 group"
                    >
                      <div className="flex items-start gap-4">
                        <div className="bg-blue-100 rounded-lg p-3">
                          <FileText className="h-6 w-6 text-blue-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-900 truncate group-hover:text-blue-600">
                            {doc.title}
                          </h3>
                          <p className="text-xs text-gray-400 mt-1">
                            {doc.document_number}
                          </p>
                          <p className="text-sm text-gray-500 mt-2 line-clamp-2">
                            {doc.description || 'No description'}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
                        <span>{formatDate(doc.created_at)}</span>
                        {doc.category && (
                          <span className="bg-gray-100 px-2 py-1 rounded">
                            {doc.category}
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {docs.items.map((doc) => (
                    <Link
                      key={doc.id}
                      to={`/doc/${doc.id}`}
                      className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-4 group"
                    >
                      <div className="flex items-center gap-4">
                        <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-gray-900 group-hover:text-blue-600">
                              {doc.title}
                            </h3>
                            <span className="text-xs text-gray-400">
                              {doc.document_number}
                            </span>
                          </div>
                          <p className="text-sm text-gray-500 truncate">
                            {doc.description || 'No description'}
                          </p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-sm text-gray-400">
                            {formatDate(doc.created_at)}
                          </div>
                          {doc.category && (
                            <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                              {doc.category}
                            </span>
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {docs.total_pages > 1 && (
                <div className="mt-8 flex justify-center items-center gap-4">
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                    className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {page} of {docs.total_pages}
                  </span>
                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= docs.total_pages}
                    className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16">
              <Folder className="h-16 w-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No documents found</h3>
              <p className="text-gray-500">
                {search ? `No documents match "${search}"` : 'No public documents available in this category'}
              </p>
              {(category || search) && (
                <button
                  onClick={() => {
                    setSearchParams({})
                    setLocalSearch('')
                  }}
                  className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
