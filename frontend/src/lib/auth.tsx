import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type { User, LoginRequest, UserCreate } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (credentials: LoginRequest) => Promise<void>
  register: (userData: UserCreate) => Promise<void>
  logout: () => Promise<void>
  isAdmin: boolean
  isEditor: boolean
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

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const isEditor = user?.role === 'editor' || isAdmin

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, isAdmin, isEditor }}>
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
