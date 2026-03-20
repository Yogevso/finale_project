import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AnalyticsDashboardPage from './AnalyticsDashboardPage'

vi.mock('@/features/analyticsDashboard/hooks/useAnalyticsDashboardController', () => ({
  useAnalyticsDashboardController: () => ({
    activeTab: 'overview',
    setActiveTab: vi.fn(),
    startDate: '2026-03-01',
    setStartDate: vi.fn(),
    endDate: '2026-03-31',
    setEndDate: vi.fn(),
    granularity: 'daily',
    setGranularity: vi.fn(),
    queryParams: {
      date_from: '2026-03-01',
      date_to: '2026-03-31',
      granularity: 'daily',
    },
    accessibleTabs: [
      { id: 'overview', label: 'Overview', icon: () => null, minRole: 'MANAGER' },
    ],
    hasAnyAccess: true,
    showExportButton: true,
  }),
}))

vi.mock('@/components/analytics/hooks/useAnalytics', () => ({
  useAnalyticsOverview: () => ({
    isLoading: false,
    data: {
      period_start: '2026-03-01',
      period_end: '2026-03-31',
      total_documents: 12,
      total_users: 8,
      total_views: 120,
      total_downloads: 33,
      documents_by_status: { draft: 5, active: 7 },
      documents_by_category: [{ category: 'Release Notes', count: 7 }],
      by_audience_type: { internal: 4, company: 6, public: 2 },
      pending_reviews: 3,
      views_today: 9,
      new_docs_this_week: 2,
      exposure_risk_transitions_30d: 1,
      assignment_churn_90d: [{ document_id: 42, churn_count: 5 }],
    },
  }),
  useRecentActivity: () => ({
    isLoading: false,
    data: [],
  }),
}))

describe('AnalyticsDashboardPage', () => {
  it('renders audience segmentation metrics from overview data', async () => {
    render(<AnalyticsDashboardPage />)

    expect(await screen.findByText('Audience Breakdown')).toBeInTheDocument()
    expect(screen.getByTestId('audience-type-internal')).toHaveTextContent('4')
    expect(screen.getByTestId('audience-type-company')).toHaveTextContent('6')
    expect(screen.getByTestId('audience-type-public')).toHaveTextContent('2')
  })
})
