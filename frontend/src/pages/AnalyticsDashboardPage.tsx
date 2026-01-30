import { useState } from 'react'
import { BarChart3, Users, FileText, MessageSquare, TrendingUp, Building2 } from 'lucide-react'
import {
  DateRangePicker,
  ExportButton,
  OverviewSection,
  EngagementSection,
  UserSection,
  ContentSection,
  FeedbackSection,
  TenantSection,
} from '@/components/analytics'
import { useAuth } from '@/lib/auth'
import type { TimeGranularity, AnalyticsQueryParams } from '@/types'

type TabType = 'overview' | 'engagement' | 'users' | 'content' | 'feedback' | 'tenant'

const tabs: { id: TabType; label: string; icon: React.ElementType; minRole: string }[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3, minRole: 'MANAGER' },
  { id: 'engagement', label: 'Engagement', icon: TrendingUp, minRole: 'MANAGER' },
  { id: 'users', label: 'Users', icon: Users, minRole: 'ADMIN' },
  { id: 'content', label: 'Content', icon: FileText, minRole: 'MANAGER' },
  { id: 'feedback', label: 'Feedback', icon: MessageSquare, minRole: 'MANAGER' },
  { id: 'tenant', label: 'Tenant', icon: Building2, minRole: 'SYSTEM_ADMIN' },
]

export default function AnalyticsDashboardPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  
  // Date range state
  const [startDate, setStartDate] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() - 30)
    return date.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0])
  const [granularity, setGranularity] = useState<TimeGranularity>('daily')

  const queryParams: AnalyticsQueryParams = {
    date_from: startDate,
    date_to: endDate,
    granularity,
  }

  // Role hierarchy for checking permissions
  const roleHierarchy: Record<string, number> = {
    viewer: 1,
    editor: 2,
    manager: 3,
    admin: 4,
    system_admin: 5,
  }

  const userRoleLevel = roleHierarchy[user?.role || 'viewer'] || 0

  const hasAccess = (minRole: string) => {
    return userRoleLevel >= (roleHierarchy[minRole.toLowerCase()] || 0)
  }

  const accessibleTabs = tabs.filter((tab) => hasAccess(tab.minRole))

  // If user doesn't have access to any tab, show access denied
  if (accessibleTabs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <BarChart3 className="w-16 h-16 text-slate-400 mx-auto mb-4" />
          <h2 className="text-xl font-display font-semibold text-slate-900 mb-2">Access Restricted</h2>
          <p className="text-slate-500">
            You need Manager or higher role to access analytics.
          </p>
        </div>
      </div>
    )
  }

  // If active tab is not accessible, switch to first accessible tab
  if (!accessibleTabs.find((t) => t.id === activeTab)) {
    setActiveTab(accessibleTabs[0].id)
  }

  const renderSection = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewSection params={queryParams} />
      case 'engagement':
        return <EngagementSection params={queryParams} />
      case 'users':
        return <UserSection params={queryParams} />
      case 'content':
        return <ContentSection params={queryParams} />
      case 'feedback':
        return <FeedbackSection params={queryParams} />
      case 'tenant':
        return <TenantSection params={queryParams} />
      default:
        return <OverviewSection params={queryParams} />
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-900">Analytics Dashboard</h1>
          <p className="text-slate-500">Insights into your content and user engagement</p>
        </div>
        {activeTab !== 'tenant' && (
          <ExportButton 
            exportType={activeTab as 'overview' | 'engagement' | 'users' | 'content' | 'feedback'} 
            startDate={startDate} 
            endDate={endDate} 
          />
        )}
      </div>

      {/* Date Range Picker */}
      <DateRangePicker
        startDate={startDate}
        endDate={endDate}
        granularity={granularity}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onGranularityChange={setGranularity}
      />

      {/* Tab Navigation */}
      <div className="surface-card rounded-2xl">
        <div className="border-b border-slate-200">
          <nav className="flex -mb-px overflow-x-auto">
            {accessibleTabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap ${
                    isActive
                      ? 'border-sky-500 text-sky-600'
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Content */}
      {renderSection()}
    </div>
  )
}
