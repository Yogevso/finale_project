import { Navigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { getHomeRouteForRole } from '@/config/routes'
import type { UserRole } from '@/types'

interface RoleGuardProps {
  children: React.ReactNode
  /** Roles allowed to access this route */
  allowedRoles?: UserRole[]
  /** If true, only internal users can access */
  internalOnly?: boolean
  /** Redirect path if access denied (defaults to role's home) */
  redirectTo?: string
}

/**
 * Guard component that restricts access based on user role.
 * Shows loading spinner while auth is being checked.
 * Redirects to login if not authenticated.
 * Redirects to appropriate home if role not allowed.
 */
export default function RoleGuard({
  children,
  allowedRoles,
  internalOnly = false,
  redirectTo,
}: RoleGuardProps) {
  const { user, isLoading } = useAuth()

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600"></div>
      </div>
    )
  }

  // Not logged in - redirect to login
  if (!user) {
    return <Navigate to="/login" replace />
  }

  // Check if internal only
  if (internalOnly && user.role === 'customer') {
    const home = redirectTo || getHomeRouteForRole(user.role)
    return <Navigate to={home} replace />
  }

  // Check if specific roles are required
  if (allowedRoles && allowedRoles.length > 0) {
    if (!allowedRoles.includes(user.role)) {
      const home = redirectTo || getHomeRouteForRole(user.role)
      return <Navigate to={home} replace />
    }
  }

  return <>{children}</>
}

/**
 * Guard specifically for admin routes (system_admin, admin only)
 */
export function AdminGuard({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRoles={['system_admin', 'admin']}>
      {children}
    </RoleGuard>
  )
}

/**
 * Guard for management routes (system_admin, admin, manager)
 */
export function ManagerGuard({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRoles={['system_admin', 'admin', 'manager']}>
      {children}
    </RoleGuard>
  )
}

/**
 * Guard for internal staff routes (everyone except customers)
 */
export function InternalGuard({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard internalOnly>
      {children}
    </RoleGuard>
  )
}

/**
 * Guard for editor-level routes (system_admin, admin, manager, editor)
 */
export function EditorGuard({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRoles={['system_admin', 'admin', 'manager', 'editor']}>
      {children}
    </RoleGuard>
  )
}
