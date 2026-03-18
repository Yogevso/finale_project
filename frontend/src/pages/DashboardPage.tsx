import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, BookMarked, BookOpen, CheckCircle2, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'

import AdminFirstCompanyWizard from '@/components/AdminFirstCompanyWizard'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'
import OnboardingChecklist from '@/components/OnboardingChecklist'
import PageHeader from '@/components/PageHeader'
import Skeleton from '@/components/Skeleton'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'

interface DashboardBookmark {
  id: number
  document_id: number
  document_title: string
  document_number?: string
}

interface DashboardProgressItem {
  id: number
  document_id: number
  document_title: string
  progress_percent: number
}

export default function DashboardPage() {
  const { user, isCustomer, isAdmin } = useAuth()
  const [isAdminWizardDismissed, setIsAdminWizardDismissed] = useState(false)
  const onboardingStorageKey = `onboarding_completed_${user?.id ?? 'unknown'}`
  const adminWizardStorageKey = useMemo(
    () => `admin-wizard-dismissed-${user?.id ?? 'unknown'}`,
    [user?.id],
  )

  useEffect(() => {
    if (!user || !isAdmin || isCustomer) {
      setIsAdminWizardDismissed(false)
      return
    }
    setIsAdminWizardDismissed(window.localStorage.getItem(adminWizardStorageKey) === '1')
  }, [adminWizardStorageKey, isAdmin, isCustomer, user])

  const { data: documents, isLoading: isDocumentsLoading } = useQuery({
    queryKey: ['documents', 'dashboard'],
    queryFn: () => api.getDocuments({ page: 1, page_size: 5 }),
  })

  const { data: documentStats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: () => api.getDocumentStats(),
  })

  const companiesOnboardingQuery = useQuery({
    queryKey: ['companies', 'onboarding-check'],
    queryFn: () => api.getCompanies({ page: 1, per_page: 1 }),
    enabled: Boolean(user && isAdmin && !isCustomer),
  })

  const { data: bookmarks = [] } = useQuery<DashboardBookmark[]>({
    queryKey: ['bookmarks', 'dashboard'],
    queryFn: () => api.getBookmarks(),
    enabled: Boolean(user),
  })

  const stats = [
    { label: 'Favorites', value: bookmarks.length, icon: BookMarked },
    { label: 'Published', value: documentStats?.published ?? 0, icon: FileText },
    { label: 'Approved', value: documentStats?.approved ?? 0, icon: CheckCircle2 },
    { label: 'Drafts', value: documentStats?.draft ?? 0, icon: BookOpen },
  ]

  const shouldShowAdminWizard =
    Boolean(user && isAdmin && !isCustomer) &&
    !isAdminWizardDismissed &&
    !companiesOnboardingQuery.isLoading &&
    (companiesOnboardingQuery.data?.total ?? 0) === 0
  const documentsPath = isCustomer ? '/portal/documents' : '/documents'

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        subtitle={`Welcome back, ${user?.full_name || 'team member'}`}
        eyebrow="Internal Portal"
      />

      {user && !shouldShowAdminWizard && (
        <OnboardingChecklist
          storageKey={onboardingStorageKey}
          role={user.role}
          documentsPath={documentsPath}
        />
      )}

      {user && shouldShowAdminWizard && (
        <AdminFirstCompanyWizard
          isOpen
          userId={user.id}
          onDismiss={() => {
            setIsAdminWizardDismissed(true)
            void companiesOnboardingQuery.refetch()
          }}
        />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="surface-card rounded-2xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="eyebrow">{stat.label}</p>
                  {isStatsLoading ? (
                    <Skeleton className="mt-1 h-9 w-16" />
                  ) : (
                    <p className="text-3xl font-display font-bold text-slate-900 mt-1">{stat.value}</p>
                  )}
                </div>
                <Icon className="h-7 w-7 text-slate-500" />
              </div>
            </div>
          )
        })}
      </div>

      <div className="surface-card rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-display font-semibold text-slate-900">Recent Documents</h2>
          <Link to={documentsPath} className="text-sm font-medium text-sky-600 hover:text-sky-700">
            View all →
          </Link>
        </div>
        <div className="divide-y divide-slate-100">
          {isDocumentsLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-4 w-44" />
            </div>
          ) : documents?.items.length === 0 ? (
            <div className="p-6 text-center text-slate-500">No documents yet</div>
          ) : (
            documents?.items.map((doc) => (
              <div key={doc.id} className="p-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <Link to={`/documents/${doc.id}/fullscreen`} className="block hover:text-sky-700">
                      <h3 className="font-medium text-slate-900">{doc.title}</h3>
                      <p className="text-sm text-slate-500">{doc.document_number}</p>
                    </Link>
                  </div>
                  <div className="flex items-center gap-3">
                    <BookmarkToggleButton documentId={doc.id} showLabel={false} />
                    <span
                      className={`pill ${
                        doc.status === 'active'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : doc.status === 'approved'
                            ? 'bg-sky-50 text-sky-700 border-sky-200'
                            : doc.status === 'draft'
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      {doc.status === 'active'
                        ? 'Published'
                        : doc.status === 'approved'
                          ? 'Approved'
                          : doc.status}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {!isCustomer && <RecentActivityWidget />}

      <div className="surface-card rounded-2xl p-6">
        <h2 className="text-lg font-display font-semibold text-slate-900 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <a href="/documents" className="btn-primary">
            View All Documents
          </a>
          <button className="btn-secondary" onClick={() => window.location.href = '/documents?action=create'}>
            Create New Document
          </button>
        </div>
      </div>

      <div className={`grid gap-6 ${isCustomer ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
        <BookmarksWidget />
        {isCustomer && <ReadingProgressWidget />}
      </div>
    </div>
  )
}

function BookmarksWidget() {
  const { user } = useAuth()
  const { data: bookmarks = [], isLoading } = useQuery<DashboardBookmark[]>({
    queryKey: ['bookmarks'],
    queryFn: () => api.getBookmarks(),
    enabled: Boolean(user),
  })

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h2 className="font-display font-semibold text-slate-900 flex items-center gap-2">
          <BookMarked className="h-4 w-4 text-amber-500" />
          My Bookmarks
        </h2>
        <span className="pill bg-slate-100 text-slate-600 border-slate-200">{bookmarks.length} saved</span>
      </div>
      <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-2">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-36" />
          </div>
        ) : bookmarks.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            <BookMarked className="h-6 w-6 mx-auto mb-2 text-slate-300" />
            <p>No bookmarks yet</p>
            <p className="text-xs mt-1">Bookmark documents for quick access</p>
          </div>
        ) : (
          bookmarks.slice(0, 5).map((bookmark) => (
            <Link
              key={bookmark.id}
              to={`/documents/${bookmark.document_id}/fullscreen`}
              className="block p-3 hover:bg-slate-50 transition-colors"
            >
              <p className="font-medium text-slate-900 text-sm truncate">{bookmark.document_title}</p>
              <p className="text-xs text-slate-500">{bookmark.document_number}</p>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}

function RecentActivityWidget() {
  const { isCustomer } = useAuth()
  const { data: activities = [], isLoading } = useQuery({
    queryKey: ['analytics', 'recent-activity'],
    queryFn: () => api.getRecentActivity(20),
    enabled: !isCustomer,
  })

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 p-4">
        <h2 className="flex items-center gap-2 font-display font-semibold text-slate-900">
          <Activity className="h-4 w-4 text-sky-600" />
          Recent Activity
        </h2>
        <span className="pill border-slate-200 bg-slate-100 text-slate-600">{activities.length} items</span>
      </div>
      <div className="max-h-80 divide-y divide-slate-100 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-3 w-52" />
            <Skeleton className="h-3 w-44" />
            <Skeleton className="h-3 w-48" />
          </div>
        ) : activities.length === 0 ? (
          <div className="p-6 text-center text-slate-500">No recent activity yet</div>
        ) : (
          activities.map((activity) => (
            <div key={activity.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-900">
                    <span className="font-medium">{activity.user_name}</span>{' '}
                    <span className="text-slate-600">{formatActivityAction(activity.action, activity.details)}</span>
                  </p>
                  {activity.document_id && activity.document_title ? (
                    <Link
                      to={`/documents/${activity.document_id}`}
                      className="mt-1 inline-block text-sm text-sky-700 hover:text-sky-800"
                    >
                      {activity.document_title}
                    </Link>
                  ) : null}
                </div>
                <span className="whitespace-nowrap text-xs text-slate-500">
                  {new Date(activity.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function formatActivityAction(action: string, details?: string) {
  if (details?.toLowerCase().includes('comment')) {
    return 'commented on a document'
  }
  if (details?.toLowerCase().includes('published')) {
    return 'published a document'
  }
  if (action === 'create') {
    return 'created a document'
  }
  if (action === 'update') {
    return 'updated a document'
  }
  if (action === 'delete') {
    return 'deleted a document'
  }
  if (action === 'download') {
    return 'downloaded a document'
  }
  return 'viewed a document'
}

function ReadingProgressWidget() {
  const { isCustomer } = useAuth()
  const { data: progress = [], isLoading } = useQuery<DashboardProgressItem[]>({
    queryKey: ['reading-progress'],
    queryFn: () => api.getReadingProgress(),
    enabled: isCustomer,
  })

  const inProgress = progress.filter((item) => item.progress_percent < 100)
  const completed = progress.filter((item) => item.progress_percent >= 100)

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h2 className="font-display font-semibold text-slate-900 flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-sky-500" />
          Reading Progress
        </h2>
        <span className="pill bg-emerald-50 text-emerald-700 border-emerald-200">{completed.length} completed</span>
      </div>
      <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-2">
            <Skeleton className="h-3 w-44" />
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
        ) : inProgress.length === 0 && completed.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            <BookOpen className="h-6 w-6 mx-auto mb-2 text-slate-300" />
            <p>No reading activity</p>
            <p className="text-xs mt-1">Start reading documents to track progress</p>
          </div>
        ) : (
          <>
            {inProgress.map((item) => (
              <Link
                key={item.id}
                to={`/documents/${item.document_id}/fullscreen`}
                className="block p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <p className="font-medium text-slate-900 text-sm truncate flex-1">{item.document_title}</p>
                  <span className="text-xs text-sky-600 ml-2">{item.progress_percent}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <div className="h-full bg-sky-500 transition-all" style={{ width: `${item.progress_percent}%` }} />
                </div>
              </Link>
            ))}
            {completed.slice(0, 3).map((item) => (
              <Link
                key={item.id}
                to={`/documents/${item.document_id}/fullscreen`}
                className="block p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <p className="font-medium text-slate-700 text-sm truncate">{item.document_title}</p>
                </div>
              </Link>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
