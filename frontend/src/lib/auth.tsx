import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { syncDateFormatPreferences } from './dateUtils'
import type { LoginRequest, Permission, User, UserCreate } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (credentials: LoginRequest) => Promise<void>
  register: (userData: UserCreate) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<User | null>
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

  const refreshUser = useCallback(async (): Promise<User | null> => {
    if (!api.hasToken()) {
      setUser(null)
      syncDateFormatPreferences(undefined, undefined)
      return null
    }

    try {
      const currentUser = await api.getCurrentUser()
      setUser(currentUser)
      syncDateFormatPreferences(currentUser.timezone, currentUser.locale)
      return currentUser
    } catch {
      api.clearTokens()
      setUser(null)
      syncDateFormatPreferences(undefined, undefined)
      return null
    }
  }, [])

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      await refreshUser()
      setIsLoading(false)
    }
    checkAuth()
  }, [refreshUser])

  const login = async (credentials: LoginRequest) => {
    // Clear all cached queries before login to ensure fresh data for new user
    queryClient.clear()
    await api.login(credentials)
    const currentUser = await refreshUser()
    if (!currentUser) {
      throw new Error('Failed to load user profile after login')
    }
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
    syncDateFormatPreferences(undefined, undefined)
  }

  // Role checks
  const isSystemAdmin = user?.role === 'system_admin'
  const isAdmin = user?.role === 'admin' || isSystemAdmin
  const isManager = user?.role === 'manager' || isAdmin
  const isEditor = user?.role === 'editor' || isManager
  const isViewer = user?.role === 'viewer' || isEditor
  const isCustomer = user?.role === 'customer'
  const isInternal = user !== null && user.role !== 'customer'

  const effectivePermissions = user?.permissions ?? []

  // Permission checks are backend-driven via /auth/me effective permissions.
  const hasPermission = (permission: Permission): boolean => {
    return effectivePermissions.includes(permission)
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
      refreshUser,
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
