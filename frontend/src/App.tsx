import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth'
import { getHomeRouteForRole } from './config/routes'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import DocumentDetailPage from './pages/DocumentDetailPage'
import DocumentFullscreenPage from './pages/DocumentFullscreenPage'
import UsersPage from './pages/UsersPage'
import CompaniesPage from './pages/CompaniesPage'
import CompanyDetailPage from './pages/CompanyDetailPage'
import ReviewsPage from './pages/ReviewsPage'
import FeedbackPage from './pages/admin/FeedbackPage'
import SystemSetupPage from './pages/admin/SystemSetupPage'
import AnalyticsDashboardPage from './pages/AnalyticsDashboardPage'
import ViewerDocumentPage from './pages/viewer/ViewerDocumentPage'
// Public portal pages
import PublicLayout from './layouts/PublicLayout'
import PublicHomePage from './pages/public/PublicHomePage'
import PublicDocumentsPage from './pages/public/PublicDocumentsPage'
import PublicDocumentPage from './pages/public/PublicDocumentPage'
import PublicSearchPage from './pages/public/PublicSearchPage'
import PublicTopicsPage from './pages/public/PublicTopicsPage'
import PublicToolsPage from './pages/public/PublicToolsPage'
import PublicHelpPage from './pages/public/PublicHelpPage'
import PublicTopicDetailPage from './pages/public/PublicTopicDetailPage'
// Customer portal pages
import CustomerLayout from './layouts/CustomerLayout'
import CustomerRoute from './components/guards/CustomerRoute'
import CustomerDashboard from './pages/portal/CustomerDashboard'
import CustomerDocumentsPage from './pages/portal/CustomerDocumentsPage'
import CustomerDocumentPage from './pages/portal/CustomerDocumentPage'
import MyFeedbackPage from './pages/portal/MyFeedbackPage'
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

function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* ==================== PUBLIC PORTAL ==================== */}
        {/* No auth required - accessible to everyone */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<RoleBasedRedirect />} />
          <Route path="/docs" element={<PublicDocumentsPage />} />
          <Route path="/browse" element={<Navigate to="/docs" replace />} />
          <Route path="/topics" element={<PublicTopicsPage />} />
          <Route path="/topics/:slug" element={<PublicTopicDetailPage />} />
          <Route path="/tools" element={<PublicToolsPage />} />
          <Route path="/help" element={<PublicHelpPage />} />
          <Route path="/doc/:id" element={<PublicDocumentPage />} />
          <Route path="/search" element={<PublicSearchPage />} />
        </Route>

        {/* Legacy viewer routes */}
        <Route path="/viewer" element={<Navigate to="/" replace />} />
        <Route path="/viewer/documents/:id" element={<ViewerDocumentPage />} />

        {/* ==================== AUTH ROUTES ==================== */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/accept-invitation" element={<AcceptInvitationPage />} />

        {/* ==================== INTERNAL STAFF ROUTES ==================== */}
        {/* Dashboard - all internal users */}
        <Route
          path="/dashboard"
          element={
            <InternalGuard>
              <Layout />
            </InternalGuard>
          }
        >
          <Route index element={<DashboardPage />} />
        </Route>

        {/* Documents - all internal users */}
        <Route
          path="/documents"
          element={
            <InternalGuard>
              <Layout />
            </InternalGuard>
          }
        >
          <Route index element={<DocumentsPage />} />
          <Route path=":id" element={<DocumentDetailPage />} />
        </Route>

        {/* Fullscreen Document View - no layout wrapper */}
        <Route
          path="/documents/:id/fullscreen"
          element={
            <InternalGuard>
              <DocumentFullscreenPage />
            </InternalGuard>
          }
        />

        {/* Reviews - editors and above */}
        <Route
          path="/reviews"
          element={
            <RoleGuard allowedRoles={['system_admin', 'admin', 'manager', 'editor']}>
              <Layout />
            </RoleGuard>
          }
        >
          <Route index element={<ReviewsPage />} />
        </Route>

        {/* ==================== MANAGEMENT ROUTES ==================== */}
        {/* Users - managers and above */}
        <Route
          path="/users"
          element={
            <ManagerGuard>
              <Layout />
            </ManagerGuard>
          }
        >
          <Route index element={<UsersPage />} />
        </Route>

        {/* Feedback - managers and above */}
        <Route
          path="/admin/feedback"
          element={
            <ManagerGuard>
              <Layout />
            </ManagerGuard>
          }
        >
          <Route index element={<FeedbackPage />} />
        </Route>

        {/* Analytics - managers and above */}
        <Route
          path="/analytics"
          element={
            <ManagerGuard>
              <Layout />
            </ManagerGuard>
          }
        >
          <Route index element={<AnalyticsDashboardPage />} />
        </Route>

        {/* ==================== ADMIN ROUTES ==================== */}
        {/* Companies - admins only */}
        <Route
          path="/admin/companies"
          element={
            <AdminGuard>
              <Layout />
            </AdminGuard>
          }
        >
          <Route index element={<CompaniesPage />} />
          <Route path=":id" element={<CompanyDetailPage />} />
        </Route>

        <Route
          path="/admin/system-setup"
          element={
            <RoleGuard allowedRoles={['system_admin']}>
              <Layout />
            </RoleGuard>
          }
        >
          <Route index element={<SystemSetupPage />} />
        </Route>

        {/* ==================== CUSTOMER PORTAL ==================== */}
        {/* Authenticated customers only */}
        <Route
          path="/portal"
          element={
            <CustomerRoute>
              <CustomerLayout />
            </CustomerRoute>
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
    </AuthProvider>
  )
}

export default App
