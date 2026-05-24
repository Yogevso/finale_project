import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, BookMarked, BookOpen, CheckCircle2, FileText } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

import AdminFirstCompanyWizard from '@/components/AdminFirstCompanyWizard'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import OnboardingChecklist from '@/components/OnboardingChecklist'
import OnboardingGuideDialog from '@/components/OnboardingGuideDialog'
import PageHeader from '@/components/PageHeader'
import Skeleton from '@/components/Skeleton'
import { useOnboarding } from '@/features/onboarding/useOnboarding'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { portalApi } from '@/lib/portalApi'

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
  const [searchParams, setSearchParams] = useSearchParams()
  const [isAdminWizardDismissed, setIsAdminWizardDismissed] = useState(false)
  const [isGuideOpen, setIsGuideOpen] = useState(false)
  const [hasAutoOpenedGuide, setHasAutoOpenedGuide] = useState(false)
  const [isChecklistCollapsed, setIsChecklistCollapsed] = useState(false)
  const adminWizardStorageKey = useMemo(
    () => `admin-wizard-dismissed-${user?.id ?? 'unknown'}`,
    [user?.id],
  )
  const onboarding = useOnboarding(user?.role)

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

  const {
    data: documentStats,
    isLoading: isStatsLoading,
    isError: isStatsError,
    refetch: refetchDocumentStats,
  } = useQuery({
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
  const shouldForceGuideOpen = searchParams.get('onboarding') === '1'

  useEffect(() => {
    if (!user || shouldShowAdminWizard || hasAutoOpenedGuide) {
      return
    }
    if (shouldForceGuideOpen || onboarding.shouldAutoOpenGuide) {
      setIsGuideOpen(true)
      setHasAutoOpenedGuide(true)
    }
  }, [
    hasAutoOpenedGuide,
    onboarding.shouldAutoOpenGuide,
    shouldForceGuideOpen,
    shouldShowAdminWizard,
    user,
  ])

  const closeGuide = () => {
    setIsGuideOpen(false)
    if (shouldForceGuideOpen) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.delete('onboarding')
      setSearchParams(nextParams, { replace: true })
    }
    if (onboarding.shouldAutoOpenGuide) {
      void onboarding.markGuideSeen()
    }
  }

  return (
    <div className="page-stack-lg">
      <PageHeader
        title="Dashboard"
        subtitle={`Welcome back, ${user?.full_name || 'team member'}`}
        eyebrow="Internal Portal"
      />

      {!shouldShowAdminWizard && (
        <OnboardingGuideDialog
          open={isGuideOpen}
          config={onboarding.config}
          onClose={closeGuide}
        />
      )}

      {user && !shouldShowAdminWizard && (
        <OnboardingChecklist
          title={onboarding.config?.checklistTitle ?? 'Welcome onboarding checklist'}
          description={
            onboarding.config?.checklistDescription ??
            'Complete these quick steps to get familiar with the workspace.'
          }
          steps={onboarding.config?.steps ?? []}
          completedSteps={onboarding.completedSteps}
          completionDate={onboarding.serverState.checklist_completed_at}
          isPending={onboarding.isPending}
          isCollapsed={isChecklistCollapsed}
          onToggleCollapsed={() => setIsChecklistCollapsed((current) => !current)}
          onToggleStep={(stepId) => {
            void onboarding.toggleChecklistStep(stepId)
          }}
          onReset={() => {
            setIsChecklistCollapsed(false)
            void onboarding.resetChecklist()
          }}
          onOpenGuide={() => setIsGuideOpen(true)}
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

      {isStatsError ? (
        <ErrorState
          title="Dashboard stats unavailable"
          message="We could not load the dashboard summary cards."
          onRetry={() => void refetchDocumentStats()}
        />
      ) : (
        <section aria-label="Dashboard summary metrics" aria-busy={isStatsLoading}>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4" role="list">
            {stats.map((stat) => {
              const Icon = stat.icon
              return (
                <div
                  key={stat.label}
                  role="listitem"
                  aria-label={`${stat.label}: ${isStatsLoading ? 'Loading' : stat.value}`}
                  className="surface-card rounded-2xl p-6"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="eyebrow">{stat.label}</p>
                      {isStatsLoading ? (
                        <Skeleton className="mt-1 h-9 w-16" />
                      ) : (
                        <p className="mt-1 text-3xl font-display font-bold text-slate-900 dark:text-slate-100">
                          {stat.value}
                        </p>
                      )}
                    </div>
                    <Icon className="h-7 w-7 text-slate-500 dark:text-slate-400" aria-hidden="true" />
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      <section className="surface-card overflow-hidden rounded-2xl" aria-labelledby="dashboard-recent-documents-heading">
        <div className="flex items-center justify-between border-b border-slate-200 p-6 dark:border-slate-800">
          <h2 id="dashboard-recent-documents-heading" className="section-title">
            Recent Documents
          </h2>
          <Link
            to={documentsPath}
            className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-300 dark:hover:text-blue-200"
          >
            View all -&gt;
          </Link>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800" role="list" aria-label="Recent documents">
          {isDocumentsLoading ? (
            <div className="space-y-3 p-6">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-4 w-44" />
            </div>
          ) : documents?.items.length === 0 ? (
            <div className="p-4" role="status">
              <EmptyState
                size="compact"
                title="No documents yet"
                description="Create or upload a document to populate your recent list."
                icon={<FileText className="h-6 w-6" aria-hidden="true" />}
              />
            </div>
          ) : (
            documents?.items.map((doc) => (
              <div key={doc.id} role="listitem" className="p-4 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/70">
                <div className="flex items-center justify-between">
                  <div>
                    <Link
                      to={`/documents/${doc.id}/fullscreen`}
                      className="block hover:text-blue-700 dark:hover:text-blue-300"
                    >
                      <h3 className="font-medium text-slate-900 dark:text-slate-100">{doc.title}</h3>
                      <p className="helper-copy">{doc.document_number}</p>
                    </Link>
                  </div>
                  <div className="flex items-center gap-3">
                    <BookmarkToggleButton documentId={doc.id} documentTitle={doc.title} showLabel={false} />
                    <span
                      className={`pill ${
                        doc.status === 'active'
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/40 dark:text-emerald-200'
                          : doc.status === 'approved'
                            ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/70 dark:bg-blue-950/40 dark:text-blue-200'
                            : doc.status === 'draft'
                              ? 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200'
                              : 'border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
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
      </section>

      {!isCustomer && <RecentActivityWidget />}

      <div className="surface-card rounded-2xl p-6">
        <h2 className="section-title mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <a href="/documents" className="btn-primary">
            View All Documents
          </a>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              window.location.href = '/documents?action=create'
            }}
          >
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
    <section className="surface-card overflow-hidden rounded-2xl" aria-labelledby="dashboard-bookmarks-heading">
      <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
        <h2 id="dashboard-bookmarks-heading" className="section-title flex items-center gap-2">
          <BookMarked className="h-4 w-4 text-amber-500" aria-hidden="true" />
          My Bookmarks
        </h2>
        <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
          {bookmarks.length} saved
        </span>
      </div>
      <div className="max-h-64 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800" role="list" aria-label="Bookmarked documents">
        {isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-36" />
          </div>
        ) : bookmarks.length === 0 ? (
          <div className="p-4" role="status">
            <EmptyState
              size="compact"
              title="No bookmarks yet"
              description="Bookmark documents for quick access."
              icon={<BookMarked className="h-6 w-6" aria-hidden="true" />}
            />
          </div>
        ) : (
          bookmarks.slice(0, 5).map((bookmark) => (
            <Link
              key={bookmark.id}
              to={`/documents/${bookmark.document_id}/fullscreen`}
              role="listitem"
              className="block p-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/70"
            >
              <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{bookmark.document_title}</p>
              <p className="helper-copy">{bookmark.document_number}</p>
            </Link>
          ))
        )}
      </div>
    </section>
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
    <section className="surface-card overflow-hidden rounded-2xl" aria-labelledby="dashboard-activity-heading">
      <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
        <h2 id="dashboard-activity-heading" className="section-title flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-600" aria-hidden="true" />
          Recent Activity
        </h2>
        <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
          {activities.length} items
        </span>
      </div>
      <div className="max-h-80 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800" role="list" aria-label="Recent activity feed">
        {isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-3 w-52" />
            <Skeleton className="h-3 w-44" />
            <Skeleton className="h-3 w-48" />
          </div>
        ) : activities.length === 0 ? (
          <div className="p-4" role="status">
            <EmptyState
              tone="info"
              size="compact"
              title="No recent activity yet"
              description="New edits, submissions, and comments will appear here."
              icon={<Activity className="h-6 w-6" aria-hidden="true" />}
            />
          </div>
        ) : (
          activities.map((activity) => (
            <div key={activity.id} role="listitem" className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-900 dark:text-slate-100">
                    <span className="font-medium">{activity.user_name}</span>{' '}
                    <span className="body-copy">
                      {formatActivityAction(activity.action, activity.details)}
                    </span>
                  </p>
                  {activity.document_id && activity.document_title ? (
                    <Link
                      to={`/documents/${activity.document_id}`}
                      className="mt-1 inline-block text-sm text-blue-700 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
                    >
                      {activity.document_title}
                    </Link>
                  ) : null}
                </div>
                <span className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                  {new Date(activity.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
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
    queryKey: ['reading-progress', isCustomer ? 'portal' : 'engagement'],
    queryFn: () => (isCustomer ? portalApi.getReadingProgress() : api.getReadingProgress()),
    enabled: isCustomer,
  })

  const inProgress = progress.filter((item) => item.progress_percent < 100)
  const completed = progress.filter((item) => item.progress_percent >= 100)

  return (
    <section className="surface-card overflow-hidden rounded-2xl" aria-labelledby="dashboard-reading-progress-heading">
      <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
        <h2 id="dashboard-reading-progress-heading" className="section-title flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-blue-500" aria-hidden="true" />
          Reading Progress
        </h2>
        <span className="pill border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/40 dark:text-emerald-200">
          {completed.length} completed
        </span>
      </div>
      <div className="max-h-64 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800" role="list" aria-label="Reading progress">
        {isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-3 w-44" />
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
        ) : inProgress.length === 0 && completed.length === 0 ? (
          <div className="p-6 text-center" role="status">
            <BookOpen className="mx-auto mb-2 h-6 w-6 text-slate-300 dark:text-slate-600" aria-hidden="true" />
            <p>No reading activity</p>
            <p className="helper-copy mt-1">Start reading documents to track progress</p>
          </div>
        ) : (
          <>
            {inProgress.map((item) => (
              <Link
                key={item.id}
                to={isCustomer ? `/portal/documents/${item.document_id}?fullscreen=1` : `/documents/${item.document_id}/fullscreen`}
                role="listitem"
                className="block p-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/70"
              >
                <div className="mb-1 flex items-center justify-between">
                  <p className="flex-1 truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                    {item.document_title}
                  </p>
                  <span className="ml-2 text-xs text-blue-600 dark:text-blue-300">{item.progress_percent}%</span>
                </div>
                <div className="progress-track h-1.5 w-full">
                  <div className="progress-fill" style={{ width: `${item.progress_percent}%` }} />
                </div>
              </Link>
            ))}
            {completed.slice(0, 3).map((item) => (
              <Link
                key={item.id}
                to={isCustomer ? `/portal/documents/${item.document_id}?fullscreen=1` : `/documents/${item.document_id}/fullscreen`}
                role="listitem"
                className="block p-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/70"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-200">{item.document_title}</p>
                </div>
              </Link>
            ))}
          </>
        )}
      </div>
    </section>
  )
}
