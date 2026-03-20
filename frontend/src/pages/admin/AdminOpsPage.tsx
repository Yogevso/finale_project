/**
 * Admin Operations Page (Wave Z)
 *
 * System-admin only dashboard for tenant management, impersonation,
 * action queue, feature flags, maintenance windows, etc.
 */

import { lazy, Suspense, useState, type ReactNode } from 'react'
import { useAuth } from '@/lib/auth'
import ErrorBoundary from '@/components/ErrorBoundary'
import PageHeader from '@/components/PageHeader'
import { CardSkeleton, ListSkeleton, TableSkeleton } from '@/components/skeletons'
import {
  Shield,
  Settings,
  Clock,
  Server,
  CheckCircle,
  Eye,
  ToggleLeft,
} from 'lucide-react'

type Tab = 'overview' | 'impersonation' | 'actions' | 'tenants' | 'features' | 'maintenance'

const SystemStatusPanel = lazy(() => import('./adminOps/SystemStatusPanel'))
const ImpersonationPanel = lazy(() => import('./adminOps/ImpersonationPanel'))
const ActionQueuePanel = lazy(() => import('./adminOps/ActionQueuePanel'))
const TenantManagementPanel = lazy(() => import('./adminOps/TenantManagementPanel'))
const FeatureMatrixPanel = lazy(() => import('./adminOps/FeatureMatrixPanel'))
const MaintenancePanel = lazy(() => import('./adminOps/MaintenancePanel'))

function AdminOpsPanelFallback({ tab }: { tab: Tab }) {
  switch (tab) {
    case 'overview':
    case 'impersonation':
      return <CardSkeleton count={4} />
    case 'actions':
    case 'features':
      return <TableSkeleton rows={6} columns={5} />
    case 'tenants':
    case 'maintenance':
      return <ListSkeleton rows={6} />
    default:
      return <CardSkeleton count={3} />
  }
}

export default function AdminOpsPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('overview')

  if (user?.role !== 'system_admin') {
    return <div className="p-8 text-red-600">Access denied. System admin only.</div>
  }

  const tabs: { key: Tab; label: string; icon: ReactNode }[] = [
    { key: 'overview', label: 'System Status', icon: <Server size={16} /> },
    { key: 'impersonation', label: 'Impersonation', icon: <Eye size={16} /> },
    { key: 'actions', label: 'Action Queue', icon: <CheckCircle size={16} /> },
    { key: 'tenants', label: 'Tenant Management', icon: <Settings size={16} /> },
    { key: 'features', label: 'Feature Matrix', icon: <ToggleLeft size={16} /> },
    { key: 'maintenance', label: 'Maintenance', icon: <Clock size={16} /> },
  ]

  let activePanel: ReactNode = null
  switch (tab) {
    case 'overview':
      activePanel = <SystemStatusPanel />
      break
    case 'impersonation':
      activePanel = <ImpersonationPanel />
      break
    case 'actions':
      activePanel = <ActionQueuePanel />
      break
    case 'tenants':
      activePanel = <TenantManagementPanel />
      break
    case 'features':
      activePanel = <FeatureMatrixPanel />
      break
    case 'maintenance':
      activePanel = <MaintenancePanel />
      break
    default:
      activePanel = null
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Admin Operations"
        subtitle="System-admin controls for impersonation, quotas, feature flags, maintenance, and action review."
        actions={
          <span className="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700">
            <Shield className="h-3.5 w-3.5" />
            System Admin
          </span>
        }
      />

      <div className="flex gap-1 border-b border-slate-200">
        {tabs.map((tabItem) => (
          <button
            key={tabItem.key}
            type="button"
            onClick={() => setTab(tabItem.key)}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === tabItem.key
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tabItem.icon}
            {tabItem.label}
          </button>
        ))}
      </div>

      <ErrorBoundary>
        <Suspense fallback={<AdminOpsPanelFallback tab={tab} />}>
          {activePanel}
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}
