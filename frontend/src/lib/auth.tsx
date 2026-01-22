import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type { User, LoginRequest, UserCreate, UserRole } from '@/types'

// Permission types matching backend
type Permission = 
  | 'view_public_docs'
  | 'view_internal_docs'
  | 'view_company_docs'
  | 'create_document'
  | 'edit_document'
  | 'delete_document'
  | 'submit_review'
  | 'approve_review'
  | 'approve_peer_review'
  | 'publish_document'
  | 'assign_companies'
  | 'add_comments'
  | 'submit_feedback'
  | 'download_attachments'
  | 'manage_users'
  | 'manage_editors'
  | 'manage_companies'
  | 'system_settings'
  | 'manage_admins'

// Permission matrix
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  system_admin: [
    'view_public_docs', 'view_internal_docs', 'view_company_docs',
    'create_document', 'edit_document', 'delete_document',
    'submit_review', 'approve_review', 'approve_peer_review',
    'publish_document', 'assign_companies',
    'add_comments', 'submit_feedback', 'download_attachments',
    'manage_users', 'manage_editors', 'manage_companies',
    'system_settings', 'manage_admins'
  ],
  admin: [
    'view_public_docs', 'view_internal_docs', 'view_company_docs',
    'create_document', 'edit_document', 'delete_document',
    'submit_review', 'approve_review', 'approve_peer_review',
    'publish_document', 'assign_companies',
    'add_comments', 'submit_feedback', 'download_attachments',
    'manage_users', 'manage_editors', 'manage_companies', 'system_settings'
  ],
  manager: [
    'view_public_docs', 'view_internal_docs', 'view_company_docs',
    'create_document', 'edit_document', 'delete_document',
    'submit_review', 'approve_review', 'approve_peer_review',
    'publish_document', 'assign_companies',
    'add_comments', 'submit_feedback', 'download_attachments',
    'manage_editors'
  ],
  editor: [
    'view_public_docs', 'view_internal_docs', 'view_company_docs',
    'create_document', 'edit_document',
    'submit_review', 'approve_peer_review',
    'add_comments', 'submit_feedback', 'download_attachments'
  ],
  viewer: [
    'view_public_docs', 'view_internal_docs', 'view_company_docs',
    'add_comments', 'submit_feedback', 'download_attachments'
  ],
  customer: [
    'view_public_docs', 'view_company_docs',
    'submit_feedback', 'download_attachments'
  ]
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (credentials: LoginRequest) => Promise<void>
  register: (userData: UserCreate) => Promise<void>
  logout: () => Promise<void>
  // Role checks
  isSystemAdmin: boolean
  isAdmin: boolean
  isManager: boolean
  isEditor: boolean
  isViewer: boolean
  isCustomer: boolean
  isInternal: boolean
  // Permission check
  hasPermission: (permission: Permission) => boolean
  // Convenience checks
  canEditDocuments: boolean
  canPublishDocuments: boolean
  canManageUsers: boolean
  canManageCompanies: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (api.hasToken()) {
        try {
          const currentUser = await api.getCurrentUser()
          setUser(currentUser)
        } catch {
          api.clearTokens()
        }
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (credentials: LoginRequest) => {
    // Clear all cached queries before login to ensure fresh data for new user
    queryClient.clear()
    await api.login(credentials)
    const currentUser = await api.getCurrentUser()
    setUser(currentUser)
  }

  const register = async (userData: UserCreate) => {
    await api.register(userData)
    // After registration, login automatically
    await login({ username: userData.username, password: userData.password })
  }

  const logout = async () => {
    await api.logout()
    // Clear all cached queries on logout so next user gets fresh data
    queryClient.clear()
    setUser(null)
  }

  // Role checks
  const isSystemAdmin = user?.role === 'system_admin'
  const isAdmin = user?.role === 'admin' || isSystemAdmin
  const isManager = user?.role === 'manager' || isAdmin
  const isEditor = user?.role === 'editor' || isManager
  const isViewer = user?.role === 'viewer' || isEditor
  const isCustomer = user?.role === 'customer'
  const isInternal = user !== null && user.role !== 'customer'

  // Permission check function
  const hasPermission = (permission: Permission): boolean => {
    if (!user) return false
    const permissions = ROLE_PERMISSIONS[user.role] || []
    return permissions.includes(permission)
  }

  // Convenience permission checks
  const canEditDocuments = hasPermission('edit_document')
  const canPublishDocuments = hasPermission('publish_document')
  const canManageUsers = hasPermission('manage_users') || hasPermission('manage_editors')
  const canManageCompanies = hasPermission('manage_companies')

  return (
    <AuthContext.Provider value={{ 
      user, 
      isLoading, 
      login, 
      register, 
      logout, 
      isSystemAdmin,
      isAdmin, 
      isManager,
      isEditor,
      isViewer,
      isCustomer,
      isInternal,
      hasPermission,
      canEditDocuments,
      canPublishDocuments,
      canManageUsers,
      canManageCompanies,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
