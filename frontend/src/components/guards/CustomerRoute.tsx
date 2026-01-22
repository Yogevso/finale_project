/**
 * CustomerRoute - Route guard for customer portal
 * Ensures user is authenticated and has customer role
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../lib/auth'

interface CustomerRouteProps {
  children: React.ReactNode
}

export default function CustomerRoute({ children }: CustomerRouteProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Redirect internal users to dashboard
  if (user.role !== 'customer') {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
