import {
  DateRangePicker,
  ExportButton,
} from '@/components/analytics'
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
    return <AnalyticsAccessDenied />
  }

  return (
    <div className="space-y-6">
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

      <AnalyticsSectionContent activeTab={controller.activeTab} queryParams={controller.queryParams} />
    </div>
  )
}
