import { BarChart3, Building2, FileText, MessageSquare, TrendingUp, Users } from 'lucide-react'
import type { ComponentType } from 'react'

import type { TimeGranularity } from '@/types'

export type AnalyticsTabType = 'overview' | 'engagement' | 'users' | 'content' | 'feedback' | 'tenant'

export type AnalyticsTabConfig = {
  id: AnalyticsTabType
  label: string
  icon: ComponentType<{ className?: string }>
  minRole: 'MANAGER' | 'ADMIN' | 'SYSTEM_ADMIN'
}

export const analyticsTabs: AnalyticsTabConfig[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3, minRole: 'MANAGER' },
  { id: 'engagement', label: 'Engagement', icon: TrendingUp, minRole: 'MANAGER' },
  { id: 'users', label: 'Users', icon: Users, minRole: 'ADMIN' },
  { id: 'content', label: 'Content', icon: FileText, minRole: 'MANAGER' },
  { id: 'feedback', label: 'Feedback', icon: MessageSquare, minRole: 'MANAGER' },
  { id: 'tenant', label: 'Tenant', icon: Building2, minRole: 'SYSTEM_ADMIN' },
]

export const roleHierarchy: Record<string, number> = {
  viewer: 1,
  editor: 2,
  manager: 3,
  admin: 4,
  system_admin: 5,
}

export function getInitialAnalyticsDateRange(): {
  startDate: string
  endDate: string
  granularity: TimeGranularity
} {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(endDate.getDate() - 30)
  return {
    startDate: startDate.toISOString().split('T')[0],
    endDate: endDate.toISOString().split('T')[0],
    granularity: 'daily',
  }
}

export function hasAnalyticsRoleAccess(
  userRole: string | undefined,
  minRole: AnalyticsTabConfig['minRole'],
): boolean {
  const userRoleLevel = roleHierarchy[userRole || 'viewer'] || 0
  return userRoleLevel >= (roleHierarchy[minRole.toLowerCase()] || 0)
}

