import type { LucideIcon } from 'lucide-react'
import {
  BookOpen,
  Building2,
  CheckCircle2,
  FileText,
  Headphones,
  House,
  LayoutDashboard,
  LineChart,
  MessageCircle,
  MessageSquare,
  MessageSquareText,
  Search,
  Settings,
  UserCog,
  Users,
} from 'lucide-react'
import type { UserRole } from '@/types'

/**
 * Route configuration with role-based access control
 */

export interface RouteConfig {
  path: string
  label: string
  icon: LucideIcon
  /** Roles that can access this route. Empty array = all authenticated users */
  allowedRoles?: UserRole[]
  /** If true, only internal users (non-customer) can access */
  internalOnly?: boolean
  /** If true, only customers can access */
  customerOnly?: boolean
  /** If true, requires admin or system_admin role */
  adminOnly?: boolean
  /** Section for grouping in sidebar */
  section?: 'main' | 'management' | 'admin'
}

// Internal staff navigation items
export const internalNavItems: RouteConfig[] = [
  {
    path: '/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    section: 'main',
    internalOnly: true,
  },
  {
    path: '/documents',
    label: 'Documents',
    icon: FileText,
    section: 'main',
    internalOnly: true,
  },
  {
    path: '/chat',
    label: 'Chat',
    icon: MessageCircle,
    section: 'main',
    internalOnly: true,
  },
  {
    path: '/reviews',
    label: 'Reviews',
    icon: CheckCircle2,
    section: 'management',
    allowedRoles: ['system_admin', 'admin', 'manager', 'editor'],
  },
  {
    path: '/admin/feedback',
    label: 'Feedback',
    icon: MessageSquare,
    section: 'management',
    allowedRoles: ['system_admin', 'admin', 'manager'],
  },
  {
    path: '/support',
    label: 'Support',
    icon: Headphones,
    section: 'management',
    allowedRoles: ['system_admin', 'admin', 'manager'],
  },
  {
    path: '/support/canned-responses',
    label: 'Canned Responses',
    icon: MessageSquareText,
    section: 'management',
    allowedRoles: ['system_admin', 'admin', 'manager'],
  },
  {
    path: '/analytics',
    label: 'Analytics',
    icon: LineChart,
    section: 'management',
    allowedRoles: ['system_admin', 'admin', 'manager'],
  },
  {
    path: '/profile',
    label: 'Profile',
    icon: UserCog,
    section: 'management',
    internalOnly: true,
  },
  {
    path: '/users',
    label: 'Users',
    icon: Users,
    section: 'admin',
    allowedRoles: ['system_admin', 'admin', 'manager'],
  },
  {
    path: '/admin/companies',
    label: 'Companies',
    icon: Building2,
    section: 'admin',
    allowedRoles: ['system_admin', 'admin'],
  },
  {
    path: '/admin/system-setup',
    label: 'System Setup',
    icon: Settings,
    section: 'admin',
    allowedRoles: ['system_admin'],
  },
]

// Customer portal navigation items
export const customerNavItems: RouteConfig[] = [
  {
    path: '/portal/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    customerOnly: true,
  },
  {
    path: '/portal/documents',
    label: 'Documents',
    icon: FileText,
    customerOnly: true,
  },
  {
    path: '/portal/feedback',
    label: 'My Feedback',
    icon: MessageSquare,
    customerOnly: true,
  },
  {
    path: '/portal/support',
    label: 'Support',
    icon: Headphones,
    customerOnly: true,
  },
]

// Public portal navigation items (no auth required)
export const publicNavItems: RouteConfig[] = [
  {
    path: '/',
    label: 'Home',
    icon: House,
  },
  {
    path: '/docs',
    label: 'Docs',
    icon: BookOpen,
  },
  {
    path: '/search',
    label: 'Search',
    icon: Search,
  },
]

/**
 * Check if a user role can access a route
 */
export function canAccessRoute(route: RouteConfig, userRole: UserRole | null): boolean {
  // If route requires specific roles
  if (route.allowedRoles && route.allowedRoles.length > 0) {
    if (!userRole) return false
    return route.allowedRoles.includes(userRole)
  }

  // Internal only routes
  if (route.internalOnly) {
    if (!userRole) return false
    return userRole !== 'customer'
  }

  // Customer only routes
  if (route.customerOnly) {
    return userRole === 'customer'
  }

  // Admin only routes
  if (route.adminOnly) {
    if (!userRole) return false
    return userRole === 'system_admin' || userRole === 'admin'
  }

  // Default: accessible to all authenticated users
  return true
}

/**
 * Get the home route for a specific role
 */
export function getHomeRouteForRole(role: UserRole | null): string {
  if (!role) return '/'

  switch (role) {
    case 'customer':
      return '/portal/dashboard'
    case 'system_admin':
    case 'admin':
    case 'manager':
    case 'editor':
    case 'viewer':
      return '/dashboard'
    default:
      return '/'
  }
}

/**
 * Filter navigation items based on user role
 */
export function getNavigationForRole(role: UserRole | null): RouteConfig[] {
  if (!role) return []

  if (role === 'customer') {
    return customerNavItems
  }

  return internalNavItems.filter(item => canAccessRoute(item, role))
}

/**
 * Get section label
 */
export function getSectionLabel(section: RouteConfig['section']): string {
  switch (section) {
    case 'main':
      return 'Main'
    case 'management':
      return 'Management'
    case 'admin':
      return 'Administration'
    default:
      return ''
  }
}
