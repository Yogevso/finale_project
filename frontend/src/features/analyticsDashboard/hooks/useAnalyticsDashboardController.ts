import { useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/lib/auth'
import type { AnalyticsQueryParams, TimeGranularity } from '@/types'

import {
  analyticsTabs,
  getInitialAnalyticsDateRange,
  hasAnalyticsRoleAccess,
  type AnalyticsTabType,
} from '../constants'

export function useAnalyticsDashboardController() {
  const { user } = useAuth()
  const initialRange = getInitialAnalyticsDateRange()
  const [activeTab, setActiveTab] = useState<AnalyticsTabType>('overview')
  const [startDate, setStartDate] = useState(initialRange.startDate)
  const [endDate, setEndDate] = useState(initialRange.endDate)
  const [granularity, setGranularity] = useState<TimeGranularity>(initialRange.granularity)

  const accessibleTabs = useMemo(
    () => analyticsTabs.filter((tab) => hasAnalyticsRoleAccess(user?.role, tab.minRole)),
    [user?.role],
  )

  useEffect(() => {
    if (accessibleTabs.length > 0 && !accessibleTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(accessibleTabs[0].id)
    }
  }, [accessibleTabs, activeTab])

  const queryParams: AnalyticsQueryParams = {
    date_from: startDate,
    date_to: endDate,
    granularity,
  }

  return {
    activeTab,
    setActiveTab,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    granularity,
    setGranularity,
    queryParams,
    accessibleTabs,
    hasAnyAccess: accessibleTabs.length > 0,
    showExportButton: activeTab !== 'tenant',
  }
}

