/**
 * CustomerDashboard - Main dashboard for customer portal
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../../lib/auth'
import { portalApi } from '../../lib/portalApi'
import {
  FileText,
  MessageSquare,
  Clock,
  CheckCircle,
  Folder,
} from 'lucide-react'

export default function CustomerDashboard() {
  const { user } = useAuth()

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['portal', 'stats'],
    queryFn: () => portalApi.getDashboardStats(),
  })

  // Fetch recent documents
  const { data: recentDocs, isLoading: docsLoading } = useQuery({
    queryKey: ['portal', 'documents', 'recent'],
    queryFn: () => portalApi.getDocuments({ per_page: 6 }),
  })

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['portal', 'categories'],
    queryFn: () => portalApi.getCategories(),
  })

  return (
    <div className="space-y-8">
      {/* Welcome header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 text-white">
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.full_name || 'Customer'}!
        </h1>
        <p className="mt-1 text-indigo-100">
          Access your documents and resources from your personalized portal.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-blue-100 rounded-lg">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Documents</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '...' : stats?.total_documents || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-green-100 rounded-lg">
              <Folder className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Company Documents</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '...' : stats?.company_documents || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-yellow-100 rounded-lg">
              <Clock className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Pending Feedback</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '...' : stats?.pending_feedback || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-purple-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Responded</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '...' : stats?.responded_feedback || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent documents */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Documents</h2>
          <Link
            to="/portal/documents"
            className="text-sm text-indigo-600 hover:text-indigo-500"
          >
            View all →
          </Link>
        </div>
        <div className="p-6">
          {docsLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : recentDocs?.items.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="h-12 w-12 mx-auto text-gray-300" />
              <p className="mt-2">No documents available yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentDocs?.items.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/portal/documents/${doc.id}`}
                  className="block p-4 border rounded-lg hover:border-indigo-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start">
                    <FileText className="h-8 w-8 text-gray-400 flex-shrink-0" />
                    <div className="ml-3 min-w-0">
                      <h3 className="font-medium text-gray-900 truncate">{doc.title}</h3>
                      {doc.description && (
                        <p className="text-sm text-gray-500 line-clamp-2 mt-1">
                          {doc.description}
                        </p>
                      )}
                      <div className="flex items-center mt-2 text-xs text-gray-400">
                        {doc.category && (
                          <span className="bg-gray-100 px-2 py-0.5 rounded mr-2">
                            {doc.category}
                          </span>
                        )}
                        <span>v{doc.version}</span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Categories */}
      {categories && categories.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Browse by Category</h2>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <Link
                  key={cat.category}
                  to={`/portal/documents?category=${encodeURIComponent(cat.category)}`}
                  className="inline-flex items-center px-4 py-2 bg-gray-100 hover:bg-indigo-100 text-gray-700 hover:text-indigo-700 rounded-full transition-colors"
                >
                  <Folder className="h-4 w-4 mr-2" />
                  {cat.category}
                  <span className="ml-2 bg-white px-2 py-0.5 rounded-full text-xs">
                    {cat.count}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/portal/documents"
          className="flex items-center p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <div className="p-3 bg-indigo-100 rounded-lg">
            <FileText className="h-8 w-8 text-indigo-600" />
          </div>
          <div className="ml-4">
            <h3 className="font-semibold text-gray-900">Browse Documents</h3>
            <p className="text-sm text-gray-500">View all available documents and resources</p>
          </div>
        </Link>

        <Link
          to="/portal/feedback"
          className="flex items-center p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <div className="p-3 bg-purple-100 rounded-lg">
            <MessageSquare className="h-8 w-8 text-purple-600" />
          </div>
          <div className="ml-4">
            <h3 className="font-semibold text-gray-900">My Feedback</h3>
            <p className="text-sm text-gray-500">View and track your feedback submissions</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
