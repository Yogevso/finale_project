import { FileText, Users, Eye, MessageSquare, Clock } from 'lucide-react'
import { StatCard } from '../StatCard'
import { DonutChartWidget } from '../DonutChartWidget'
import { useAnalyticsOverview, useRecentActivity } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams, RecentActivity } from '@/types'
import { formatDistanceToNow } from 'date-fns'

interface OverviewSectionProps {
  params?: AnalyticsQueryParams
}

export function OverviewSection({ params }: OverviewSectionProps) {
  const { data: overview, isLoading: overviewLoading } = useAnalyticsOverview(params)
  const { data: recentActivity, isLoading: activityLoading } = useRecentActivity(10)

  const documentsByStatus = overview
    ? Object.entries(overview.documents_by_status).map(([status, count]) => ({
        name: status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' '),
        value: count,
      }))
    : []

  const getActivityIcon = (action: RecentActivity['action']) => {
    if (action.includes('view')) return <Eye className="w-4 h-4 text-sky-500" />
    if (action.includes('comment')) return <MessageSquare className="w-4 h-4 text-emerald-500" />
    if (action.includes('review')) return <FileText className="w-4 h-4 text-purple-500" />
    if (action.includes('status')) return <Clock className="w-4 h-4 text-orange-500" />
    return <FileText className="w-4 h-4 text-slate-500" />
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-900">Overview</h2>
      
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Documents"
          value={overview?.total_documents || 0}
          icon={FileText}
          loading={overviewLoading}
          subtitle={`${overview?.new_docs_this_week || 0} new this week`}
        />
        <StatCard
          title="Total Users"
          value={overview?.total_users || 0}
          icon={Users}
          loading={overviewLoading}
        />
        <StatCard
          title="Total Views"
          value={overview?.total_views?.toLocaleString() || 0}
          icon={Eye}
          loading={overviewLoading}
          subtitle={`${overview?.views_today || 0} today`}
        />
        <StatCard
          title="Pending Reviews"
          value={overview?.pending_reviews || 0}
          icon={MessageSquare}
          loading={overviewLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4">Documents by Category</h3>
          {overviewLoading ? (
            <div className="animate-pulse h-64 bg-slate-100 rounded"></div>
          ) : overview?.documents_by_category && overview.documents_by_category.length > 0 ? (
            <ul className="space-y-2">
              {overview.documents_by_category.map((cat, idx) => (
                <li key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <span className="text-sm font-medium text-slate-700">{cat.category || 'Uncategorized'}</span>
                  <span className="text-sm font-bold text-slate-900">{cat.count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-center py-4">No categories</p>
          )}
        </div>
        <DonutChartWidget
          title="Documents by Status"
          data={documentsByStatus}
          loading={overviewLoading}
          centerLabel="Total"
          centerValue={overview?.total_documents}
        />
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-medium text-slate-900 mb-4">Recent Activity</h3>
        {activityLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 animate-pulse">
                <div className="w-8 h-8 bg-slate-200 rounded-full"></div>
                <div className="flex-1 h-4 bg-slate-200 rounded"></div>
              </div>
            ))}
          </div>
        ) : recentActivity && recentActivity.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {recentActivity.map((activity: RecentActivity) => (
              <li key={activity.id} className="py-3 flex items-center gap-4">
                <div className="p-2 bg-slate-50 rounded-full">
                  {getActivityIcon(activity.action)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {activity.document_title || activity.action}
                  </p>
                  <p className="text-xs text-slate-500">
                    {activity.user_name} • {activity.action.replace('_', ' ')}
                  </p>
                </div>
                <span className="text-xs text-slate-400">
                  {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500 text-center py-4">No recent activity</p>
        )}
      </div>
    </div>
  )
}
