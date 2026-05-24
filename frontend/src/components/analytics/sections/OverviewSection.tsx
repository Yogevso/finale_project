import { FileText, Users, Eye, MessageSquare, Clock, ShieldAlert } from 'lucide-react'
import { StatCard } from '../StatCard'
import { DonutChartWidget } from '../DonutChartWidget'
import { useAnalyticsOverview, useRecentActivity } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams, AssignmentChurnItem, RecentActivity } from '@/types'
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
  const audienceByType = overview?.by_audience_type || {
    internal: 0,
    company: 0,
    public: 0,
  }
  const topChurnItems = (overview?.assignment_churn_90d || []).slice(0, 5)

  const getActivityIcon = (action: RecentActivity['action']) => {
    if (action.includes('view')) return <Eye className="w-4 h-4 text-blue-500" />
    if (action.includes('comment')) return <MessageSquare className="w-4 h-4 text-emerald-500" />
    if (action.includes('review')) return <FileText className="w-4 h-4 text-purple-500" />
    if (action.includes('status')) return <Clock className="w-4 h-4 text-orange-500" />
    return <FileText className="w-4 h-4 text-slate-500" />
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-900">Overview</h2>
      
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
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
        <StatCard
          title="Exposure Risk (30d)"
          value={overview?.exposure_risk_transitions_30d || 0}
          icon={ShieldAlert}
          loading={overviewLoading}
          subtitle="Internal -> Public transitions"
        />
      </div>

      <div className="bg-white rounded-xl shadow p-6" data-testid="audience-segmentation-chart">
        <h3 className="text-lg font-medium text-slate-900 mb-4">Audience Breakdown</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-xl border border-slate-200 p-4 bg-slate-50" data-testid="audience-type-internal">
            <div className="text-xs uppercase tracking-wide text-slate-500">Internal</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{audienceByType.internal || 0}</div>
          </div>
          <div className="rounded-xl border border-slate-200 p-4 bg-slate-50" data-testid="audience-type-company">
            <div className="text-xs uppercase tracking-wide text-slate-500">Client-visible</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{audienceByType.company || 0}</div>
          </div>
          <div className="rounded-xl border border-slate-200 p-4 bg-slate-50" data-testid="audience-type-public">
            <div className="text-xs uppercase tracking-wide text-slate-500">Public</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{audienceByType.public || 0}</div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4">Documents by Category</h3>
          {overviewLoading ? (
            <div className="animate-pulse h-64 bg-slate-100 rounded"></div>
          ) : overview?.documents_by_category && overview.documents_by_category.length > 0 ? (
            <div className="max-h-80 overflow-auto pr-2">
              <ul className="space-y-2">
                {overview.documents_by_category.map((cat, idx) => (
                  <li
                    key={idx}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-white transition"
                  >
                    <span className="text-sm font-medium text-slate-700">
                      {cat.category || 'Uncategorized'}
                    </span>
                    <span className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
                      {cat.count}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
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

      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-medium text-slate-900 mb-4">Assignment Churn (90d)</h3>
        {overviewLoading ? (
          <div className="animate-pulse h-24 bg-slate-100 rounded"></div>
        ) : topChurnItems.length > 0 ? (
          <ul className="space-y-2">
            {topChurnItems.map((item: AssignmentChurnItem) => (
              <li
                key={item.document_id}
                className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-3 py-2"
              >
                <span className="text-sm text-slate-700">Document #{item.document_id}</span>
                <span className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
                  {item.churn_count} changes
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500 text-sm">No assignment churn in the selected period.</p>
        )}
      </div>
    </div>
  )
}
