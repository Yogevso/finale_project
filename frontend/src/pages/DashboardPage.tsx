import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function DashboardPage() {
  const { user, isCustomer } = useAuth()
  
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', 'dashboard'],
    queryFn: () => api.getDocuments({ page: 1, page_size: 5 }),
  })

  const stats = [
    { label: 'Total Documents', value: documents?.total ?? 0, icon: '📄', color: 'blue' },
    { label: 'Active', value: documents?.items.filter(d => d.status === 'active').length ?? 0, icon: '✅', color: 'green' },
    { label: 'Draft', value: documents?.items.filter(d => d.status === 'draft').length ?? 0, icon: '📝', color: 'yellow' },
    { label: 'Archived', value: documents?.items.filter(d => d.status === 'archived').length ?? 0, icon: '📦', color: 'gray' },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="section-title">Dashboard</h1>
        <p className="text-slate-500 mt-1">Welcome back, {user?.full_name}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="surface-card rounded-2xl p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="eyebrow">{stat.label}</p>
                <p className="text-3xl font-display font-bold text-slate-900 mt-1">
                  {isLoading ? '...' : stat.value}
                </p>
              </div>
              <div className="text-3xl">{stat.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Documents */}
      <div className="surface-card rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-display font-semibold text-slate-900">Recent Documents</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {isLoading ? (
            <div className="p-6 text-center text-slate-500">Loading...</div>
          ) : documents?.items.length === 0 ? (
            <div className="p-6 text-center text-slate-500">No documents yet</div>
          ) : (
            documents?.items.map((doc) => (
              <div key={doc.id} className="p-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-slate-900">{doc.title}</h3>
                    <p className="text-sm text-slate-500">{doc.document_number}</p>
                  </div>
                  <span
                    className={`pill ${
                      doc.status === 'active'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : doc.status === 'draft'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}
                  >
                    {doc.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="surface-card rounded-2xl p-6">
        <h2 className="text-lg font-display font-semibold text-slate-900 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <a
            href="/documents"
            className="btn-primary"
          >
            View All Documents
          </a>
          <button
            className="btn-secondary"
            onClick={() => window.location.href = '/documents?action=create'}
          >
            Create New Document
          </button>
        </div>
      </div>

      {/* Engagement Widgets */}
      <div className={`grid gap-6 ${isCustomer ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
        {/* Bookmarks */}
        {isCustomer && <BookmarksWidget />}
        
        {/* Reading Progress */}
        {isCustomer && <ReadingProgressWidget />}
      </div>
    </div>
  )
}

function BookmarksWidget() {
  const { isCustomer } = useAuth()
  const { data: bookmarks = [], isLoading } = useQuery({
    queryKey: ['bookmarks'],
    queryFn: () => api.getBookmarks(),
    enabled: isCustomer,
  })

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h2 className="font-display font-semibold text-slate-900 flex items-center gap-2">
          ★ My Bookmarks
        </h2>
        <span className="pill bg-slate-100 text-slate-600 border-slate-200">{bookmarks.length} saved</span>
      </div>
      <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-slate-500">Loading...</div>
        ) : bookmarks.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            <div className="text-2xl mb-2">☆</div>
            <p>No bookmarks yet</p>
            <p className="text-xs mt-1">Bookmark documents for quick access</p>
          </div>
        ) : (
          bookmarks.slice(0, 5).map((b: any) => (
            <Link
              key={b.id}
              to={`/documents/${b.document_id}`}
              className="block p-3 hover:bg-slate-50 transition-colors"
            >
              <p className="font-medium text-slate-900 text-sm truncate">{b.document_title}</p>
              <p className="text-xs text-slate-500">{b.document_number}</p>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}

function ReadingProgressWidget() {
  const { isCustomer } = useAuth()
  const { data: progress = [], isLoading } = useQuery({
    queryKey: ['reading-progress'],
    queryFn: () => api.getReadingProgress(),
    enabled: isCustomer,
  })

  const inProgress = progress.filter((p: any) => p.progress_percent < 100)
  const completed = progress.filter((p: any) => p.progress_percent >= 100)

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h2 className="font-display font-semibold text-slate-900 flex items-center gap-2">
          📖 Reading Progress
        </h2>
        <span className="pill bg-emerald-50 text-emerald-700 border-emerald-200">{completed.length} completed</span>
      </div>
      <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-slate-500">Loading...</div>
        ) : inProgress.length === 0 && completed.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            <div className="text-2xl mb-2">📚</div>
            <p>No reading activity</p>
            <p className="text-xs mt-1">Start reading documents to track progress</p>
          </div>
        ) : (
          <>
            {inProgress.map((p: any) => (
              <Link
                key={p.id}
                to={`/documents/${p.document_id}`}
                className="block p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <p className="font-medium text-slate-900 text-sm truncate flex-1">{p.document_title}</p>
                  <span className="text-xs text-sky-600 ml-2">{p.progress_percent}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-sky-500 transition-all"
                    style={{ width: `${p.progress_percent}%` }}
                  />
                </div>
              </Link>
            ))}
            {completed.slice(0, 3).map((p: any) => (
              <Link
                key={p.id}
                to={`/documents/${p.document_id}`}
                className="block p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-emerald-500">✓</span>
                  <p className="font-medium text-slate-700 text-sm truncate">{p.document_title}</p>
                </div>
              </Link>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
