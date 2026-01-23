import { Users, FileText, Eye, Activity } from 'lucide-react'
import { StatCard } from '../StatCard'
import { LeaderboardTable } from '../LeaderboardTable'
import { useTenantAnalytics } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams, TenantMetrics } from '@/types'

interface TenantSectionProps {
  params?: AnalyticsQueryParams
}

export function TenantSection({ params }: TenantSectionProps) {
  const { data: tenantAnalytics, isLoading } = useTenantAnalytics(params)

  const tenantsByDocuments = tenantAnalytics?.tenants.map((t: TenantMetrics, idx: number) => ({
    rank: idx + 1,
    name: t.tenant_name,
    value: t.total_documents,
    subValue: `${t.total_users} users`,
  })) || []

  const tenantsByUsers = tenantAnalytics?.tenants
    .slice()
    .sort((a: TenantMetrics, b: TenantMetrics) => b.total_users - a.total_users)
    .map((t: TenantMetrics, idx: number) => ({
      rank: idx + 1,
      name: t.tenant_name,
      value: t.total_users,
      subValue: `${t.active_users_30d} active`,
    })) || []

  const tenantsByViews = tenantAnalytics?.tenants
    .slice()
    .sort((a: TenantMetrics, b: TenantMetrics) => b.total_views_30d - a.total_views_30d)
    .map((t: TenantMetrics, idx: number) => ({
      rank: idx + 1,
      name: t.tenant_name,
      value: t.total_views_30d,
      subValue: `Health: ${t.health_score}%`,
    })) || []

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Tenant Analytics</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Tenants"
          value={tenantAnalytics?.total_tenants || 0}
          icon={Users}
          loading={isLoading}
        />
        <StatCard
          title="Active Tenants"
          value={tenantAnalytics?.active_tenants || 0}
          icon={Activity}
          loading={isLoading}
        />
        <StatCard
          title="Total Documents"
          value={tenantAnalytics?.tenants.reduce((sum: number, t: TenantMetrics) => sum + t.total_documents, 0) || 0}
          icon={FileText}
          loading={isLoading}
        />
        <StatCard
          title="Total Views (30d)"
          value={tenantAnalytics?.tenants.reduce((sum: number, t: TenantMetrics) => sum + t.total_views_30d, 0).toLocaleString() || 0}
          icon={Eye}
          loading={isLoading}
        />
      </div>

      {/* Leaderboards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <LeaderboardTable
          title="By Documents"
          items={tenantsByDocuments}
          valueLabel="Docs"
          loading={isLoading}
        />
        <LeaderboardTable
          title="By Users"
          items={tenantsByUsers}
          valueLabel="Users"
          loading={isLoading}
        />
        <LeaderboardTable
          title="By Views (30d)"
          items={tenantsByViews}
          valueLabel="Views"
          loading={isLoading}
        />
      </div>

      {/* Tenant Health */}
      {tenantAnalytics?.tenants && tenantAnalytics.tenants.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Tenant Health Scores</h3>
          <div className="space-y-4">
            {tenantAnalytics.tenants.map((tenant: TenantMetrics) => (
              <div key={tenant.tenant_id} className="flex items-center gap-4">
                <span className="w-40 text-sm font-medium text-gray-700 truncate">
                  {tenant.tenant_name}
                </span>
                <div className="flex-1 bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${
                      tenant.health_score >= 80 ? 'bg-green-500' :
                      tenant.health_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${tenant.health_score}%` }}
                  />
                </div>
                <span className="w-12 text-sm font-bold text-gray-900 text-right">
                  {tenant.health_score}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
