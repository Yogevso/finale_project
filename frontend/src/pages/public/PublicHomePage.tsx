import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Search, ArrowRight, Folder, BookOpen } from 'lucide-react'
import { useState } from 'react'
import { publicApi } from '@/lib/publicApi'

export default function PublicHomePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  // Fetch recent public documents
  const { data: recentDocs, isLoading: docsLoading } = useQuery({
    queryKey: ['public-documents', { page: 1, page_size: 6 }],
    queryFn: () => publicApi.getDocuments({ page: 1, page_size: 6 }),
  })

  // Fetch categories
  const { data: categories, isLoading: categoriesLoading } = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['public-stats'],
    queryFn: () => publicApi.getStats(),
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-blue-600 to-blue-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              Document Portal
            </h1>
            <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
              Access our public documentation library. Browse technical guides,
              user manuals, and knowledge base articles.
            </p>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-6 py-4 pl-14 rounded-xl text-gray-900 text-lg focus:outline-none focus:ring-4 focus:ring-blue-300"
                />
                <Search className="absolute left-5 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <button
                  type="submit"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
                >
                  Search
                </button>
              </div>
            </form>

            {/* Stats */}
            {stats && (
              <div className="flex justify-center gap-8 mt-10">
                <div className="text-center">
                  <div className="text-3xl font-bold">{stats.total_documents}</div>
                  <div className="text-blue-200">Documents</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold">{stats.total_categories}</div>
                  <div className="text-blue-200">Categories</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Browse by Category</h2>
            <Link
              to="/browse"
              className="text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
            >
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {categoriesLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-24 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : categories?.items && categories.items.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {categories.items.slice(0, 8).map((cat) => (
                <Link
                  key={cat.category}
                  to={`/browse?category=${encodeURIComponent(cat.category)}`}
                  className="bg-gray-50 hover:bg-gray-100 rounded-lg p-6 text-center transition-colors group"
                >
                  <Folder className="h-8 w-8 text-blue-500 mx-auto mb-3 group-hover:scale-110 transition-transform" />
                  <h3 className="font-medium text-gray-900">{cat.category}</h3>
                  <p className="text-sm text-gray-500">{cat.count} documents</p>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <Folder className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No categories available yet.</p>
            </div>
          )}
        </div>
      </section>

      {/* Recent Documents Section */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Recent Documents</h2>
            <Link
              to="/browse"
              className="text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
            >
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {docsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-48 bg-white rounded-lg shadow animate-pulse" />
              ))}
            </div>
          ) : recentDocs?.items && recentDocs.items.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {recentDocs.items.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/doc/${doc.id}`}
                  className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 group"
                >
                  <div className="flex items-start gap-4">
                    <div className="bg-blue-100 rounded-lg p-3 group-hover:bg-blue-200 transition-colors">
                      <FileText className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 truncate group-hover:text-blue-600">
                        {doc.title}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {doc.description || 'No description available'}
                      </p>
                      {doc.category && (
                        <span className="inline-block mt-2 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {doc.category}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <BookOpen className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No public documents available yet.</p>
              <p className="text-sm mt-2">Check back later for new content!</p>
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Need access to more documents?
          </h2>
          <p className="text-gray-600 mb-6">
            Login to access internal documentation, company-specific resources, and more.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium"
          >
            Login for full access
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  )
}
