import { Eye, Clock, MousePointer } from 'lucide-react'
import { StatCard } from '../StatCard'
import { LineChartWidget } from '../LineChartWidget'
import { LeaderboardTable } from '../LeaderboardTable'
import { useEngagementAnalytics, useTopDocuments } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams, DocumentStats } from '@/types'

interface EngagementSectionProps {
  params?: AnalyticsQueryParams
}

export function EngagementSection({ params }: EngagementSectionProps) {
  const { data: engagement, isLoading: engagementLoading } = useEngagementAnalytics(params)
  const { data: topDocs, isLoading: topDocsLoading } = useTopDocuments(10, params)

  const topDocumentsForTable = topDocs?.by_views.map((doc: DocumentStats, idx: number) => ({
    rank: idx + 1,
    name: doc.title,
    value: doc.view_count,
    subValue: doc.document_number,
  })) || []

  // Format time duration
  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${Math.round(minutes)}m`
    return `${Math.round(minutes / 60)}h ${Math.round(minutes % 60)}m`
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Engagement Analytics</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Unique Visitors"
          value={engagement?.unique_visitors?.toLocaleString() || 0}
          icon={Eye}
          loading={engagementLoading}
        />
        <StatCard
          title="Avg. Reading Progress"
          value={`${Math.round((engagement?.avg_reading_progress || 0) * 100)}%`}
          icon={MousePointer}
          loading={engagementLoading}
        />
        <StatCard
          title="Completion Rate"
          value={`${Math.round((engagement?.completion_rate || 0) * 100)}%`}
          icon={Clock}
          loading={engagementLoading}
        />
        <StatCard
          title="Time Spent"
          value={formatDuration(engagement?.total_time_spent_minutes || 0)}
          icon={Clock}
          loading={engagementLoading}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LineChartWidget
          title="Views Over Time"
          data={engagement?.views_over_time || []}
          loading={engagementLoading}
          color="#3B82F6"
          label="Views"
          secondaryData={engagement?.downloads_over_time}
          secondaryColor="#10B981"
          secondaryLabel="Downloads"
        />
        <LeaderboardTable
          title="Top Documents by Views"
          items={topDocumentsForTable}
          valueLabel="Views"
          loading={topDocsLoading}
        />
      </div>

      {/* Top Downloads */}
      {topDocs?.by_downloads && topDocs.by_downloads.length > 0 && (
        <LeaderboardTable
          title="Top Documents by Downloads"
          items={topDocs.by_downloads.map((doc: DocumentStats, idx: number) => ({
            rank: idx + 1,
            name: doc.title,
            value: doc.download_count,
            subValue: doc.document_number,
          }))}
          valueLabel="Downloads"
          loading={topDocsLoading}
        />
      )}
    </div>
  )
}
