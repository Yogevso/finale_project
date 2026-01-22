/**
 * CustomerDocumentsPage - Document listing for customer portal
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { portalApi } from '../../lib/portalApi'
import {
  FileText,
  Folder,
  Search,
  LayoutGrid,
  List,
  Paperclip,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

export default function CustomerDocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  const page = parseInt(searchParams.get('page') || '1')
  const category = searchParams.get('category') || undefined
  const search = searchParams.get('search') || undefined

  // Fetch documents
  const { data: documents, isLoading } = useQuery({
    queryKey: ['portal', 'documents', { page, category, search }],
    queryFn: () => portalApi.getDocuments({ page, category, search, per_page: 12 }),
  })

  // Fetch categories for filter
  const { data: categories } = useQuery({
    queryKey: ['portal', 'categories'],
    queryFn: () => portalApi.getCategories(),
  })

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const query = formData.get('search') as string
    if (query) {
      setSearchParams({ search: query })
    } else {
      searchParams.delete('search')
      setSearchParams(searchParams)
    }
  }

  const handleCategoryChange = (cat: string | null) => {
    if (cat) {
      searchParams.set('category', cat)
    } else {
      searchParams.delete('category')
    }
    searchParams.delete('page')
    setSearchParams(searchParams)
  }

  const handlePageChange = (newPage: number) => {
    searchParams.set('page', String(newPage))
    setSearchParams(searchParams)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="mt-1 text-gray-500">Browse all available documents and resources</p>
      </div>

      {/* Search and filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="search"
                name="search"
                defaultValue={search}
                placeholder="Search documents..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </form>

          {/* Category filter */}
          <select
            value={category || ''}
            onChange={(e) => handleCategoryChange(e.target.value || null)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Categories</option>
            {categories?.map((cat) => (
              <option key={cat.category} value={cat.category}>
                {cat.category} ({cat.count})
              </option>
            ))}
          </select>

          {/* View toggle */}
          <div className="flex border rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-indigo-100 text-indigo-600' : 'text-gray-500 hover:bg-gray-100'}`}
            >
              <LayoutGrid className="h-5 w-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-indigo-100 text-indigo-600' : 'text-gray-500 hover:bg-gray-100'}`}
            >
              <List className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Active filters */}
        {(category || search) && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t">
            <span className="text-sm text-gray-500">Filters:</span>
            {category && (
              <span className="inline-flex items-center px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm">
                <Folder className="h-4 w-4 mr-1" />
                {category}
                <button
                  onClick={() => handleCategoryChange(null)}
                  className="ml-2 hover:text-indigo-900"
                >
                  ×
                </button>
              </span>
            )}
            {search && (
              <span className="inline-flex items-center px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                "{search}"
                <button
                  onClick={() => {
                    searchParams.delete('search')
                    setSearchParams(searchParams)
                  }}
                  className="ml-2 hover:text-gray-900"
                >
                  ×
                </button>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Documents */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
        </div>
      ) : documents?.items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <FileText className="h-16 w-16 mx-auto text-gray-300" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No documents found</h3>
          <p className="mt-2 text-gray-500">
            {search || category
              ? 'Try adjusting your search or filters'
              : 'No documents are available at this time'}
          </p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents?.items.map((doc) => (
            <Link
              key={doc.id}
              to={`/portal/documents/${doc.id}`}
              className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-5"
            >
              <div className="flex items-start">
                <FileText className="h-10 w-10 text-indigo-500 flex-shrink-0" />
                <div className="ml-4 flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{doc.title}</h3>
                  {doc.description && (
                    <p className="text-sm text-gray-500 line-clamp-2 mt-1">{doc.description}</p>
                  )}
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
                <div className="flex items-center gap-2">
                  {doc.category && (
                    <span className="bg-gray-100 px-2 py-0.5 rounded">{doc.category}</span>
                  )}
                  {doc.has_attachments && (
                    <Paperclip className="h-4 w-4" />
                  )}
                </div>
                <span>v{doc.version}</span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow divide-y">
          {documents?.items.map((doc) => (
            <Link
              key={doc.id}
              to={`/portal/documents/${doc.id}`}
              className="block p-4 hover:bg-gray-50"
            >
              <div className="flex items-center">
                <FileText className="h-8 w-8 text-indigo-500 flex-shrink-0" />
                <div className="ml-4 flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900">{doc.title}</h3>
                  {doc.description && (
                    <p className="text-sm text-gray-500 truncate">{doc.description}</p>
                  )}
                </div>
                <div className="ml-4 flex items-center gap-3 text-sm text-gray-400">
                  {doc.category && (
                    <span className="bg-gray-100 px-2 py-0.5 rounded">{doc.category}</span>
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
      {documents && documents.pages > 1 && (
        <div className="flex items-center justify-between bg-white rounded-lg shadow px-4 py-3">
          <p className="text-sm text-gray-500">
            Showing {(page - 1) * 12 + 1} to {Math.min(page * 12, documents.total)} of{' '}
            {documents.total} results
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page === 1}
              className="p-2 rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <span className="px-4 py-2 text-sm">
              Page {page} of {documents.pages}
            </span>
            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page === documents.pages}
              className="p-2 rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
