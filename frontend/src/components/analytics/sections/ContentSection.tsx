import { FileText, Check, MessageSquare, Clock } from 'lucide-react'
import { StatCard } from '../StatCard'
import { DonutChartWidget } from '../DonutChartWidget'
import { LineChartWidget } from '../LineChartWidget'
import { useContentAnalytics } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams } from '@/types'

interface ContentSectionProps {
  params?: AnalyticsQueryParams
}

export function ContentSection({ params }: ContentSectionProps) {
  const { data: contentAnalytics, isLoading } = useContentAnalytics(params)

  const reviewsByStatus = contentAnalytics
    ? Object.entries(contentAnalytics.reviews_by_status).map(([status, count]) => ({
        name: status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' '),
        value: count as number,
      }))
    : []

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Content Analytics</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Documents Created"
          value={contentAnalytics?.total_documents_created || 0}
          icon={FileText}
          loading={isLoading}
        />
        <StatCard
          title="Versions Published"
          value={contentAnalytics?.total_versions_published || 0}
          icon={Check}
          loading={isLoading}
        />
        <StatCard
          title="Total Comments"
          value={contentAnalytics?.total_comments || 0}
          icon={MessageSquare}
          loading={isLoading}
        />
        <StatCard
          title="Approval Rate"
          value={`${Math.round((contentAnalytics?.approval_rate || 0) * 100)}%`}
          icon={Check}
          loading={isLoading}
        />
      </div>

      {/* Review Turnaround */}
      {contentAnalytics?.avg_review_turnaround_hours !== null && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-50 rounded-full">
              <Clock className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Avg. Review Turnaround</p>
              <p className="text-2xl font-bold text-gray-900">
                {contentAnalytics?.avg_review_turnaround_hours?.toFixed(1) || 'N/A'} hours
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LineChartWidget
          title="Documents Created Over Time"
          data={contentAnalytics?.documents_created_over_time || []}
          loading={isLoading}
          color="#3B82F6"
        />
        <DonutChartWidget
          title="Reviews by Status"
          data={reviewsByStatus}
          loading={isLoading}
        />
      </div>

      {/* More Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LineChartWidget
          title="Versions Published Over Time"
          data={contentAnalytics?.versions_published_over_time || []}
          loading={isLoading}
          color="#10B981"
        />
        <LineChartWidget
          title="Comments Over Time"
          data={contentAnalytics?.comments_over_time || []}
          loading={isLoading}
          color="#8B5CF6"
        />
      </div>
    </div>
  )
}
