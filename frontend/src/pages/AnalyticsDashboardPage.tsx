import {
  DateRangePicker,
  ExportButton,
} from '@/components/analytics'
import ErrorBoundary from '@/components/ErrorBoundary'
import PageHeader from '@/components/PageHeader'
import {
  AnalyticsAccessDenied,
  AnalyticsSectionContent,
  AnalyticsTabsNav,
  useAnalyticsDashboardController,
} from '@/features/analyticsDashboard'

export default function AnalyticsDashboardPage() {
  const controller = useAnalyticsDashboardController()

  if (!controller.hasAnyAccess) {
    return (
      <div className="animate-fade-in">
        <AnalyticsAccessDenied />
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Analytics Dashboard"
        subtitle="Insights into your content and user engagement"
        actions={
          controller.showExportButton ? (
            <ExportButton
              exportType={controller.activeTab as 'overview' | 'engagement' | 'users' | 'content' | 'feedback'}
              startDate={controller.startDate}
              endDate={controller.endDate}
            />
          ) : undefined
        }
      />

      <DateRangePicker
        startDate={controller.startDate}
        endDate={controller.endDate}
        granularity={controller.granularity}
        onStartDateChange={controller.setStartDate}
        onEndDateChange={controller.setEndDate}
        onGranularityChange={controller.setGranularity}
      />

      <AnalyticsTabsNav
        activeTab={controller.activeTab}
        tabs={controller.accessibleTabs}
        onTabChange={controller.setActiveTab}
      />

      <ErrorBoundary>
        <AnalyticsSectionContent key={controller.activeTab} activeTab={controller.activeTab} queryParams={controller.queryParams} />
      </ErrorBoundary>
    </div>
  )
}
