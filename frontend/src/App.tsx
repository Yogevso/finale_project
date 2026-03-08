import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { AuthProvider, useAuth } from './lib/auth'
import { getHomeRouteForRole } from './config/routes'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const DocumentDetailPage = lazy(() => import('./pages/DocumentDetailPage'))
const UsersPage = lazy(() => import('./pages/UsersPage'))
const CompaniesPage = lazy(() => import('./pages/CompaniesPage'))
const CompanyDetailPage = lazy(() => import('./pages/CompanyDetailPage'))
const ReviewsPage = lazy(() => import('./pages/ReviewsPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const FeedbackPage = lazy(() => import('./pages/admin/FeedbackPage'))
const SystemSetupPage = lazy(() => import('./pages/admin/SystemSetupPage'))
const AnalyticsDashboardPage = lazy(() => import('./pages/AnalyticsDashboardPage'))
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
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-slate-300">404</h1>
        <p className="text-xl text-slate-600 mt-4">Page not found</p>
        <a href={homePath} className="mt-6 inline-block px-6 py-3 bg-sky-600 text-white rounded-xl hover:bg-sky-700">
          Go Home
        </a>
      </div>
    </div>
  )
}

function RouteLoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-600"></div>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <Toaster position="top-right" richColors />
      <Suspense fallback={<RouteLoadingFallback />}>
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
        </Route>

        {/* ==================== CATCH ALL ==================== */}
        <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  )
}

export default App
