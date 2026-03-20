import { lazy, Suspense } from 'react'
import { ChartSkeleton, StatCardSkeleton, TableSkeleton } from '@/components/skeletons'
import type { AnalyticsQueryParams } from '@/types'

import type { AnalyticsTabType } from '../constants'

type AnalyticsSectionContentProps = {
  activeTab: AnalyticsTabType
  queryParams: AnalyticsQueryParams
}

const OverviewSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/OverviewSection')).OverviewSection,
}))
const EngagementSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/EngagementSection')).EngagementSection,
}))
const UserSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/UserSection')).UserSection,
}))
const ContentSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/ContentSection')).ContentSection,
}))
const FeedbackSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/FeedbackSection')).FeedbackSection,
}))
const SearchSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/SearchSection')).SearchSection,
}))
const TenantSection = lazy(async () => ({
  default: (await import('@/components/analytics/sections/TenantSection')).TenantSection,
}))

function AnalyticsSectionFallback({ activeTab }: { activeTab: AnalyticsTabType }) {
  const showStats =
    activeTab === 'overview' ||
    activeTab === 'engagement' ||
    activeTab === 'users' ||
    activeTab === 'content' ||
    activeTab === 'feedback' ||
    activeTab === 'tenant'

  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded-full bg-slate-200" />
      {showStats ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <StatCardSkeleton key={index} />
          ))}
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartSkeleton variant={activeTab === 'overview' ? 'pie' : 'line'} />
        <ChartSkeleton variant="bar" />
      </div>
      <TableSkeleton rows={5} columns={4} />
    </div>
  )
}

export function AnalyticsSectionContent({ activeTab, queryParams }: AnalyticsSectionContentProps) {
  return (
    <Suspense fallback={<AnalyticsSectionFallback activeTab={activeTab} />}>
      {activeTab === 'overview' ? <OverviewSection params={queryParams} /> : null}
      {activeTab === 'engagement' ? <EngagementSection params={queryParams} /> : null}
      {activeTab === 'users' ? <UserSection params={queryParams} /> : null}
      {activeTab === 'content' ? <ContentSection params={queryParams} /> : null}
      {activeTab === 'feedback' ? <FeedbackSection params={queryParams} /> : null}
      {activeTab === 'search' ? <SearchSection /> : null}
      {activeTab === 'tenant' ? <TenantSection params={queryParams} /> : null}
    </Suspense>
  )
}
