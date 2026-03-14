import {
  ContentSection,
  EngagementSection,
  FeedbackSection,
  OverviewSection,
  SearchSection,
  TenantSection,
  UserSection,
} from '@/components/analytics'
import type { AnalyticsQueryParams } from '@/types'

import type { AnalyticsTabType } from '../constants'

type AnalyticsSectionContentProps = {
  activeTab: AnalyticsTabType
  queryParams: AnalyticsQueryParams
}

export function AnalyticsSectionContent({ activeTab, queryParams }: AnalyticsSectionContentProps) {
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
    case 'search':
      return <SearchSection />
    case 'tenant':
      return <TenantSection params={queryParams} />
    default:
      return <OverviewSection params={queryParams} />
  }
}

