/**
 * CustomerDashboard - Main dashboard for customer portal
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ErrorState } from '@/components/ErrorState'
import { useAuth } from '../../lib/auth'
import { portalApi } from '../../lib/portalApi'
import PageHeader from '@/components/PageHeader'
import { StatCardSkeleton } from '@/components/skeletons'
import {
  FileText,
  MessageSquare,
  Clock,
  CheckCircle,
  Folder,
  BookOpen,
  PlayCircle,
} from 'lucide-react'

export default function CustomerDashboard() {
  const { user } = useAuth()

  const {
    data: stats,
    isLoading: statsLoading,
    isError: isStatsError,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['portal', 'stats'],
    queryFn: () => portalApi.getDashboardStats(),
  })

  const { data: recentDocs, isLoading: docsLoading } = useQuery({
    queryKey: ['portal', 'documents', 'recent'],
    queryFn: () => portalApi.getDocuments({ per_page: 6 }),
  })

  const { data: categories } = useQuery({
    queryKey: ['portal', 'categories'],
    queryFn: () => portalApi.getCategories(),
  })

  const { data: continueReading } = useQuery({
    queryKey: ['portal', 'continue-reading'],
    queryFn: () => portalApi.getContinueReading(4),
  })

  const { data: recentlyViewed } = useQuery({
    queryKey: ['portal', 'recently-viewed'],
    queryFn: () => portalApi.getRecentlyViewed(6),
  })

  return (
    <div className="page-stack-lg">
      <PageHeader
        eyebrow="Customer Portal"
        title={`Welcome back, ${user?.full_name || 'Customer'}!`}
        subtitle="Access your documents and resources from your personalized portal."
      />

      {isStatsError ? (
        <ErrorState
          title="Dashboard stats unavailable"
          message="We could not load your customer dashboard summary."
          onRetry={() => void refetchStats()}
        />
      ) : statsLoading ? (
        <StatCardSkeleton count={4} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="surface-card rounded-2xl p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 rounded-xl bg-sky-100 p-3 dark:bg-sky-950/50">
                <FileText className="h-6 w-6 text-sky-600" />
              </div>
              <div className="ml-4">
                <p className="eyebrow">Total Documents</p>
                <p className="metric-value">
                  {stats?.total_documents || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="surface-card rounded-2xl p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 rounded-xl bg-emerald-100 p-3 dark:bg-emerald-950/50">
                <Folder className="h-6 w-6 text-emerald-600" />
              </div>
              <div className="ml-4">
                <p className="eyebrow">Company Documents</p>
                <p className="metric-value">
                  {stats?.company_documents || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="surface-card rounded-2xl p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 rounded-xl bg-amber-100 p-3 dark:bg-amber-950/50">
                <Clock className="h-6 w-6 text-amber-600" />
              </div>
              <div className="ml-4">
                <p className="eyebrow">Pending Feedback</p>
                <p className="metric-value">
                  {stats?.pending_feedback || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="surface-card rounded-2xl p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 rounded-xl bg-violet-100 p-3 dark:bg-violet-950/50">
                <CheckCircle className="h-6 w-6 text-violet-600 dark:text-violet-300" />
              </div>
              <div className="ml-4">
                <p className="eyebrow">Responded</p>
                <p className="metric-value">
                  {stats?.responded_feedback || 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {continueReading && continueReading.length > 0 && (
        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <h2 className="section-title flex items-center">
              <PlayCircle className="mr-2 h-5 w-5 text-sky-600" />
              Continue Reading
            </h2>
            <p className="body-copy">Pick up where you left off</p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {continueReading.map((item) => (
                <Link
                  key={item.document_id}
                  to={`/portal/documents/${item.document_id}?fullscreen=1`}
                  className="flex items-center rounded-xl border border-slate-200 p-4 transition-all hover:border-sky-300 hover:shadow-sm dark:border-slate-800 dark:hover:border-sky-700"
                >
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-sky-50 dark:bg-sky-950/40">
                    <BookOpen className="h-6 w-6 text-sky-600" />
                  </div>
                  <div className="ml-3 min-w-0 flex-1">
                    <h3 className="card-title truncate">{item.title}</h3>
                    {item.category && (
                      <span className="helper-copy">{item.category}</span>
                    )}
                    <div className="progress-track mt-1.5 h-1.5 w-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="progress-fill"
                        style={{ width: `${item.progress_percent}%` }}
                      />
                    </div>
                    <span className="helper-copy">
                      {item.progress_percent}% complete
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {recentlyViewed && recentlyViewed.length > 0 && (
        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <h2 className="section-title flex items-center">
              <Clock className="mr-2 h-5 w-5 text-slate-500 dark:text-slate-400" />
              Recently Viewed
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recentlyViewed.map((item) => (
                <Link
                  key={item.document_id}
                  to={`/portal/documents/${item.document_id}?fullscreen=1`}
                  className="block rounded-xl border border-slate-200 p-4 transition-all hover:border-sky-300 hover:shadow-sm dark:border-slate-800 dark:hover:border-sky-700"
                >
                  <div className="flex items-start">
                    <FileText className="h-6 w-6 flex-shrink-0 text-slate-400 dark:text-slate-500" />
                    <div className="ml-3 min-w-0">
                      <h3 className="card-title truncate">
                        {item.title}
                      </h3>
                      {item.category && (
                        <span className="helper-copy">{item.category}</span>
                      )}
                      {item.last_read_at && (
                        <p className="helper-copy mt-1">
                          {new Date(item.last_read_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="surface-card rounded-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h2 className="section-title">
            Recent Documents
          </h2>
          <Link
            to="/portal/documents"
            className="btn-secondary table-action-btn"
          >
            View all -&gt;
          </Link>
        </div>
        <div className="p-6">
          {docsLoading ? (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-sky-600"></div>
            </div>
          ) : recentDocs?.items.length === 0 ? (
            <div className="py-8 text-center text-slate-500 dark:text-slate-400">
              <FileText className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" />
              <p className="mt-2">No documents available yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recentDocs?.items.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/portal/documents/${doc.id}?fullscreen=1`}
                  className="block rounded-xl border border-slate-200 p-4 transition-all hover:border-sky-300 hover:shadow-md dark:border-slate-800 dark:hover:border-sky-700"
                >
                  <div className="flex items-start">
                    <FileText className="h-8 w-8 flex-shrink-0 text-slate-400 dark:text-slate-500" />
                    <div className="ml-3 min-w-0">
                      <h3 className="card-title truncate">{doc.title}</h3>
                      {doc.description && (
                        <p className="body-copy mt-1 line-clamp-2">
                          {doc.description}
                        </p>
                      )}
                      <div className="helper-copy mt-2 flex items-center">
                        {doc.category && (
                          <span className="mr-2 pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
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

      {categories && categories.length > 0 && (
        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <h2 className="section-title">
              Browse by Category
            </h2>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <Link
                  key={cat.category}
                  to={`/portal/documents?category=${encodeURIComponent(cat.category)}`}
                  className="inline-flex items-center rounded-full bg-slate-100 px-4 py-2 text-slate-700 transition-colors hover:bg-sky-100 hover:text-sky-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-sky-950/50 dark:hover:text-sky-200"
                >
                  <Folder className="mr-2 h-4 w-4" />
                  {cat.category}
                  <span className="ml-2 rounded-full bg-white px-2 py-0.5 text-xs dark:bg-slate-950 dark:text-slate-200">
                    {cat.count}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Link
          to="/portal/documents"
          className="surface-card-hover flex items-center rounded-2xl p-6"
        >
          <div className="rounded-xl bg-sky-100 p-3 dark:bg-sky-950/50">
            <FileText className="h-8 w-8 text-sky-600" />
          </div>
          <div className="ml-4">
            <h3 className="card-title">
              Browse Documents
            </h3>
            <p className="body-copy">
              View all available documents and resources
            </p>
          </div>
        </Link>

        <Link
          to="/portal/feedback"
          className="surface-card-hover flex items-center rounded-2xl p-6"
        >
          <div className="rounded-xl bg-violet-100 p-3 dark:bg-violet-950/50">
            <MessageSquare className="h-8 w-8 text-violet-600 dark:text-violet-300" />
          </div>
          <div className="ml-4">
            <h3 className="card-title">
              My Feedback
            </h3>
            <p className="body-copy">
              View and track your feedback submissions
            </p>
          </div>
        </Link>
      </div>
    </div>
  )
}
