import { describe, expect, it } from 'vitest'

import { getInitialAnalyticsDateRange, hasAnalyticsRoleAccess } from './constants'

describe('analytics dashboard constants', () => {
  it('provides an initial analytics date range', () => {
    const range = getInitialAnalyticsDateRange()
    expect(range.startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(range.endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(range.granularity).toBe('daily')
  })

  it('evaluates role access correctly', () => {
    expect(hasAnalyticsRoleAccess('manager', 'MANAGER')).toBe(true)
    expect(hasAnalyticsRoleAccess('editor', 'MANAGER')).toBe(false)
    expect(hasAnalyticsRoleAccess('system_admin', 'SYSTEM_ADMIN')).toBe(true)
    expect(hasAnalyticsRoleAccess(undefined, 'MANAGER')).toBe(false)
  })
})

