import { MessageSquare, Clock, Check, TrendingUp } from 'lucide-react'
import { StatCard } from '../StatCard'
import { BarChartWidget } from '../BarChartWidget'
import { DonutChartWidget } from '../DonutChartWidget'
import { LineChartWidget } from '../LineChartWidget'
import { useFeedbackAnalytics } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams } from '@/types'

interface FeedbackSectionProps {
  params?: AnalyticsQueryParams
}

export function FeedbackSection({ params }: FeedbackSectionProps) {
  const { data: feedbackAnalytics, isLoading } = useFeedbackAnalytics(params)

  const feedbackByStatus = feedbackAnalytics
    ? Object.entries(feedbackAnalytics.feedback_by_status).map(([status, count]) => ({
        name: status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' '),
        value: count as number,
      }))
    : []

  const feedbackByType = feedbackAnalytics
    ? Object.entries(feedbackAnalytics.feedback_by_type).map(([type, count]) => ({
        name: type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' '),
        value: count as number,
      }))
    : []

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-900">Feedback Analytics</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Feedback"
          value={feedbackAnalytics?.total_feedback || 0}
          icon={MessageSquare}
          loading={isLoading}
        />
        <StatCard
          title="Pending"
          value={feedbackAnalytics?.pending_feedback || 0}
          icon={Clock}
          loading={isLoading}
        />
        <StatCard
          title="Responded"
          value={feedbackAnalytics?.responded_feedback || 0}
          icon={Check}
          loading={isLoading}
        />
        <StatCard
          title="Helpfulness Rate"
          value={`${Math.round((feedbackAnalytics?.helpfulness_rate || 0) * 100)}%`}
          icon={TrendingUp}
          loading={isLoading}
        />
      </div>

      {/* Response Time */}
      {feedbackAnalytics?.avg_response_time_hours !== null && (
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-50 rounded-full">
              <Clock className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Avg. Response Time</p>
              <p className="text-2xl font-bold text-slate-900">
                {feedbackAnalytics?.avg_response_time_hours?.toFixed(1) || 'N/A'} hours
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DonutChartWidget
          title="Feedback by Status"
          data={feedbackByStatus}
          loading={isLoading}
          centerLabel="Total"
          centerValue={feedbackAnalytics?.total_feedback}
        />
        <BarChartWidget
          title="Feedback by Type"
          data={feedbackByType}
          loading={isLoading}
          horizontal
        />
      </div>

      {/* Timeline */}
      <LineChartWidget
        title="Feedback Over Time"
        data={feedbackAnalytics?.feedback_over_time || []}
        loading={isLoading}
        color="#10B981"
      />
    </div>
  )
}
