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
      <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-2xl p-6 text-white">
        <h1 className="text-2xl font-display font-bold">
          Welcome back, {user?.full_name || 'Customer'}!
        </h1>
        <p className="mt-1 text-slate-300">
          Access your documents and resources from your personalized portal.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-sky-100 rounded-xl">
              <FileText className="h-6 w-6 text-sky-600" />
            </div>
            <div className="ml-4">
              <p className="eyebrow">Total Documents</p>
              <p className="text-2xl font-display font-semibold text-slate-900">
                {statsLoading ? '...' : stats?.total_documents || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-emerald-100 rounded-xl">
              <Folder className="h-6 w-6 text-emerald-600" />
            </div>
            <div className="ml-4">
              <p className="eyebrow">Company Documents</p>
              <p className="text-2xl font-display font-semibold text-slate-900">
                {statsLoading ? '...' : stats?.company_documents || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-amber-100 rounded-xl">
              <Clock className="h-6 w-6 text-amber-600" />
            </div>
            <div className="ml-4">
              <p className="eyebrow">Pending Feedback</p>
              <p className="text-2xl font-display font-semibold text-slate-900">
                {statsLoading ? '...' : stats?.pending_feedback || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-purple-100 rounded-xl">
              <CheckCircle className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="eyebrow">Responded</p>
              <p className="text-2xl font-display font-semibold text-slate-900">
                {statsLoading ? '...' : stats?.responded_feedback || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent documents */}
      <div className="surface-card rounded-2xl">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-display font-semibold text-slate-900">Recent Documents</h2>
          <Link
            to="/portal/documents"
            className="text-sm text-sky-600 hover:text-sky-700 font-medium"
          >
            View all →
          </Link>
        </div>
        <div className="p-6">
          {docsLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600"></div>
            </div>
          ) : recentDocs?.items.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <FileText className="h-12 w-12 mx-auto text-slate-300" />
              <p className="mt-2">No documents available yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentDocs?.items.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/portal/documents/${doc.id}?fullscreen=1`}
                  className="block p-4 border border-slate-200 rounded-xl hover:border-sky-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start">
                    <FileText className="h-8 w-8 text-slate-400 flex-shrink-0" />
                    <div className="ml-3 min-w-0">
                      <h3 className="font-medium text-slate-900 truncate">{doc.title}</h3>
                      {doc.description && (
                        <p className="text-sm text-slate-500 line-clamp-2 mt-1">
                          {doc.description}
                        </p>
                      )}
                      <div className="flex items-center mt-2 text-xs text-slate-400">
                        {doc.category && (
                          <span className="pill bg-slate-100 text-slate-600 border-slate-200 mr-2">
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
        <div className="surface-card rounded-2xl">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="text-lg font-display font-semibold text-slate-900">Browse by Category</h2>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <Link
                  key={cat.category}
                  to={`/portal/documents?category=${encodeURIComponent(cat.category)}`}
                  className="inline-flex items-center px-4 py-2 bg-slate-100 hover:bg-sky-100 text-slate-700 hover:text-sky-700 rounded-full transition-colors"
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
          className="flex items-center p-6 surface-card-hover rounded-2xl"
        >
          <div className="p-3 bg-sky-100 rounded-xl">
            <FileText className="h-8 w-8 text-sky-600" />
          </div>
          <div className="ml-4">
            <h3 className="font-display font-semibold text-slate-900">Browse Documents</h3>
            <p className="text-sm text-slate-500">View all available documents and resources</p>
          </div>
        </Link>

        <Link
          to="/portal/feedback"
          className="flex items-center p-6 surface-card-hover rounded-2xl"
        >
          <div className="p-3 bg-purple-100 rounded-xl">
            <MessageSquare className="h-8 w-8 text-purple-600" />
          </div>
          <div className="ml-4">
            <h3 className="font-display font-semibold text-slate-900">My Feedback</h3>
            <p className="text-sm text-slate-500">View and track your feedback submissions</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
