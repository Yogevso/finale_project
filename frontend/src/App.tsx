import { lazy, Suspense, useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Toaster } from 'sonner'
import { CheckCircle2 } from 'lucide-react'
import { AuthProvider, useAuth } from './lib/auth'
import { getHomeRouteForRole } from './config/routes'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const DocumentDetailPage = lazy(() => import('./pages/DocumentDetailPage'))
const VersionComparePage = lazy(() => import('./pages/VersionComparePage'))
const UsersPage = lazy(() => import('./pages/UsersPage'))
const CompaniesPage = lazy(() => import('./pages/CompaniesPage'))
const CompanyDetailPage = lazy(() => import('./pages/CompanyDetailPage'))
const ReviewsPage = lazy(() => import('./pages/ReviewsPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const ProfileSettingsPage = lazy(() => import('./pages/ProfileSettingsPage'))
const SessionsPage = lazy(() => import('./pages/SessionsPage'))
const SecurityEventsPage = lazy(() => import('./pages/SecurityEventsPage'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'))
const FeedbackPage = lazy(() => import('./pages/admin/FeedbackPage'))
const SystemSetupPage = lazy(() => import('./pages/admin/SystemSetupPage'))
const AdminOpsPage = lazy(() => import('./pages/admin/AdminOpsPage'))
const AnalyticsDashboardPage = lazy(() => import('./pages/AnalyticsDashboardPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const AssistantPage = lazy(() => import('./pages/AssistantPage'))
const SupportPage = lazy(() => import('./pages/SupportPage'))
const CannedResponsesPage = lazy(() => import('./pages/CannedResponsesPage'))
const AccessibilityStatementPage = lazy(() => import('./pages/AccessibilityStatementPage'))
const CustomerSupportPage = lazy(() => import('./pages/portal/CustomerSupportPage'))
const ViewerDocumentPage = lazy(() => import('./pages/viewer/ViewerDocumentPage'))
// Public portal pages
import PublicLayout from './layouts/PublicLayout'
const PublicDocumentsPage = lazy(() => import('./pages/public/PublicDocumentsPage'))
const PublicPlatformsPage = lazy(() => import('./pages/public/PublicPlatformsPage'))
const PublicPlatformDetailPage = lazy(() => import('./pages/public/PublicPlatformDetailPage'))
const PublicDocumentPage = lazy(() => import('./pages/public/PublicDocumentPage'))
const PublicSearchPage = lazy(() => import('./pages/public/PublicSearchPage'))
const PublicToolsPage = lazy(() => import('./pages/public/PublicToolsPage'))
const PublicHelpPage = lazy(() => import('./pages/public/PublicHelpPage'))
const PublicChangelogPage = lazy(() => import('./pages/public/PublicChangelogPage'))
// Customer portal pages
import CustomerLayout from './layouts/CustomerLayout'
import CustomerRoute from './components/guards/CustomerRoute'
const CustomerDashboard = lazy(() => import('./pages/portal/CustomerDashboard'))
const CustomerDocumentsPage = lazy(() => import('./pages/portal/CustomerDocumentsPage'))
const CustomerDocumentPage = lazy(() => import('./pages/portal/CustomerDocumentPage'))
const MyFeedbackPage = lazy(() => import('./pages/portal/MyFeedbackPage'))
import AcceptInvitationPage from './pages/AcceptInvitationPage'
// Route guards
import RoleGuard, { InternalGuard, AdminGuard, ManagerGuard } from './components/guards/RoleGuard'
import { RouteAnnouncer } from './components/a11y/SkipNavLink'
import RouteTransition from './components/RouteTransition'
import { useTheme } from './hooks/useTheme'

// Smart redirect based on user role
function RoleBasedRedirect() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600"></div>
      </div>
    )
  }

  // If logged in, redirect to role-appropriate home
  if (user) {
    return <Navigate to={getHomeRouteForRole(user.role)} replace />
  }

  // Not logged in, redirect to public browse page
  return <Navigate to="/docs" replace />
}

// 404 page component
function NotFoundPage() {
  const { user } = useAuth()
  const homePath = user ? getHomeRouteForRole(user.role) : '/'
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (search.trim()) {
      navigate(`/search?q=${encodeURIComponent(search.trim())}`)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="text-center max-w-lg">
        <h1 className="text-6xl font-bold text-slate-300">404</h1>
        <p className="text-xl text-slate-600 mt-4">Page not found</p>
        <p className="text-slate-500 mt-2">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <form onSubmit={handleSearch} className="mt-6 flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documentation..."
            className="flex-1 px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
          />
          <button
            type="submit"
            className="px-5 py-3 bg-sky-600 text-white rounded-xl hover:bg-sky-700 font-medium"
          >
            Search
          </button>
        </form>
        <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
          <a href={homePath} className="px-6 py-3 bg-sky-600 text-white rounded-xl hover:bg-sky-700">
            Go Home
          </a>
          <a href="/docs" className="px-6 py-3 border border-slate-300 text-slate-700 rounded-xl hover:bg-slate-100">
            Browse Documents
          </a>
        </div>
      </div>
    </div>
  )
}

function RouteLoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50" role="status" aria-label="Loading page">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-600"></div>
    </div>
  )
}

/** AC-010: Announce route changes to screen readers */
function RouteChangeAnnouncer() {
  const location = useLocation()
  const [announcement, setAnnouncement] = useState('')

  useEffect(() => {
    // Derive a human-readable page name from the path
    const path = location.pathname
    const name = path === '/' ? 'Home' : path.split('/').filter(Boolean).map(s => s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ')).join(' - ')
    setAnnouncement(`Navigated to ${name}`)
  }, [location.pathname])

  return <RouteAnnouncer message={announcement} />
}

function App() {
  const { theme } = useTheme()

  return (
    <AuthProvider>
      <Toaster
        position="top-right"
        richColors
        theme={theme}
        icons={{
          success: <CheckCircle2 className="motion-enter-scale h-4 w-4 text-emerald-500" />,
        }}
        toastOptions={{
          classNames: {
            toast:
              'motion-enter-slide border border-slate-200 bg-white text-slate-900 shadow-lg dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100',
            title: 'text-slate-900 dark:text-slate-100',
            description: 'text-slate-600 dark:text-slate-300',
            success: 'border-emerald-200/80 dark:border-emerald-900/70',
            icon: 'motion-enter-scale',
            actionButton:
              'bg-sky-600 text-white hover:bg-sky-500 focus-visible:ring-sky-400',
            cancelButton:
              'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800',
            closeButton:
              'border-slate-200 bg-white text-slate-500 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:text-white',
          },
        }}
      />
      <RouteChangeAnnouncer />
      <Suspense fallback={<RouteLoadingFallback />}>
        <RouteTransition>
          <Routes>
        {/* ==================== PUBLIC PORTAL ==================== */}
        {/* No auth required - accessible to everyone */}
        <Route
          element={(
            <ErrorBoundary>
              <PublicLayout />
            </ErrorBoundary>
          )}
        >
          <Route path="/" element={<RoleBasedRedirect />} />
          <Route path="/docs" element={<PublicDocumentsPage />} />
          <Route path="/platforms" element={<PublicPlatformsPage />} />
          <Route path="/platforms/:platformId" element={<PublicPlatformDetailPage />} />
          <Route path="/browse" element={<Navigate to="/docs" replace />} />
          <Route path="/topics" element={<Navigate to="/docs" replace />} />
          <Route path="/topics/:slug" element={<Navigate to="/docs" replace />} />
          <Route path="/tools" element={<PublicToolsPage />} />
          <Route path="/help" element={<PublicHelpPage />} />
          <Route path="/changelog" element={<PublicChangelogPage />} />
          <Route path="/accessibility" element={<AccessibilityStatementPage />} />
          <Route path="/doc/:id" element={<PublicDocumentPage />} />
          <Route path="/search" element={<PublicSearchPage />} />
        </Route>

        {/* Legacy viewer routes */}
        <Route
          path="/viewer"
          element={(
            <ErrorBoundary>
              <Navigate to="/" replace />
            </ErrorBoundary>
          )}
        />
        <Route
          path="/viewer/documents/:id"
          element={(
            <ErrorBoundary>
              <ViewerDocumentPage />
            </ErrorBoundary>
          )}
        />

        {/* ==================== AUTH ROUTES ==================== */}
        <Route
          path="/login"
          element={(
            <ErrorBoundary>
              <LoginPage />
            </ErrorBoundary>
          )}
        />
        <Route
          path="/reset-password"
          element={(
            <ErrorBoundary>
              <ResetPasswordPage />
            </ErrorBoundary>
          )}
        />
        <Route
          path="/accept-invitation"
          element={(
            <ErrorBoundary>
              <AcceptInvitationPage />
            </ErrorBoundary>
          )}
        />

        {/* ==================== INTERNAL STAFF ROUTES ==================== */}
        {/* Dashboard - all internal users */}
        <Route
          path="/dashboard"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <Layout />
              </InternalGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<DashboardPage />} />
        </Route>

        {/* Documents - all internal users */}
        <Route
          path="/documents"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <Layout />
              </InternalGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<DocumentsPage />} />
          <Route path=":id" element={<DocumentDetailPage />} />
          <Route path=":id/compare" element={<VersionComparePage />} />
        </Route>

        {/* Fullscreen Document View - use DocumentDetailPage */}
        <Route
          path="/documents/:id/fullscreen"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <DocumentDetailPage />
              </InternalGuard>
            </ErrorBoundary>
          }
        />

        {/* Reviews - editors and above */}
        <Route
          path="/reviews"
          element={
            <ErrorBoundary>
              <RoleGuard allowedRoles={['system_admin', 'admin', 'manager', 'editor']}>
                <Layout />
              </RoleGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<ReviewsPage />} />
        </Route>

        {/* Notifications - all internal users */}
        <Route
          path="/notifications"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <Layout />
              </InternalGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<NotificationsPage />} />
        </Route>

        {/* Profile settings - all authenticated internal users */}
        <Route
          path="/profile"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <Layout />
              </InternalGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<ProfileSettingsPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="security-events" element={<SecurityEventsPage />} />
        </Route>

        {/* Chat - all internal users */}
        <Route
          path="/chat"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <Layout />
              </InternalGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<ChatPage />} />
        </Route>

        {/* AI Assistant - all internal users */}
        <Route
          path="/assistant"
          element={
            <ErrorBoundary>
              <InternalGuard>
                <Layout />
              </InternalGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<AssistantPage />} />
        </Route>

        {/* Support - managers and above */}
        <Route
          path="/support"
          element={
            <ErrorBoundary>
              <ManagerGuard>
                <Layout />
              </ManagerGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<SupportPage />} />
          <Route path="canned-responses" element={<CannedResponsesPage />} />
        </Route>

        {/* ==================== MANAGEMENT ROUTES ==================== */}
        {/* Users - managers and above */}
        <Route
          path="/users"
          element={
            <ErrorBoundary>
              <ManagerGuard>
                <Layout />
              </ManagerGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<UsersPage />} />
        </Route>

        {/* Feedback - managers and above */}
        <Route
          path="/admin/feedback"
          element={
            <ErrorBoundary>
              <ManagerGuard>
                <Layout />
              </ManagerGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<FeedbackPage />} />
        </Route>

        {/* Analytics - managers and above */}
        <Route
          path="/analytics"
          element={
            <ErrorBoundary>
              <ManagerGuard>
                <Layout />
              </ManagerGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<AnalyticsDashboardPage />} />
        </Route>

        {/* ==================== ADMIN ROUTES ==================== */}
        {/* Companies - admins only */}
        <Route
          path="/admin/companies"
          element={
            <ErrorBoundary>
              <AdminGuard>
                <Layout />
              </AdminGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<CompaniesPage />} />
          <Route path=":id" element={<CompanyDetailPage />} />
        </Route>

        <Route
          path="/admin/system-setup"
          element={
            <ErrorBoundary>
              <RoleGuard allowedRoles={['system_admin']}>
                <Layout />
              </RoleGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<SystemSetupPage />} />
        </Route>

        {/* Admin Operations (Wave Z) - system_admin only */}
        <Route
          path="/admin/operations"
          element={
            <ErrorBoundary>
              <RoleGuard allowedRoles={['system_admin']}>
                <Layout />
              </RoleGuard>
            </ErrorBoundary>
          }
        >
          <Route index element={<AdminOpsPage />} />
        </Route>

        {/* ==================== CUSTOMER PORTAL ==================== */}
        {/* Authenticated customers only */}
        <Route
          path="/portal"
          element={
            <ErrorBoundary>
              <CustomerRoute>
                <CustomerLayout />
              </CustomerRoute>
            </ErrorBoundary>
          }
        >
          <Route index element={<Navigate to="/portal/dashboard" replace />} />
          <Route path="dashboard" element={<CustomerDashboard />} />
          <Route path="documents" element={<CustomerDocumentsPage />} />
          <Route path="documents/:id" element={<CustomerDocumentPage />} />
          <Route path="feedback" element={<MyFeedbackPage />} />
          <Route path="support" element={<CustomerSupportPage />} />
          <Route path="assistant" element={<AssistantPage />} />
        </Route>

        {/* ==================== CATCH ALL ==================== */}
        <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </RouteTransition>
      </Suspense>
    </AuthProvider>
  )
}

export default App
