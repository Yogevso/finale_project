import { describe, expect, it } from 'vitest'

import { getDefaultAudienceForRole } from './audienceDefaults'

describe('audience defaults by role', () => {
  it('defaults to internal for internal user roles', () => {
    expect(getDefaultAudienceForRole('system_admin')).toBe('internal')
    expect(getDefaultAudienceForRole('admin')).toBe('internal')
    expect(getDefaultAudienceForRole('manager')).toBe('internal')
    expect(getDefaultAudienceForRole('editor')).toBe('internal')
  })

  it('defaults to public for viewer role', () => {
    expect(getDefaultAudienceForRole('viewer')).toBe('public')
  })

  it('defaults to company for customer role', () => {
    expect(getDefaultAudienceForRole('customer')).toBe('company')
  })

  it('falls back to public when role is missing', () => {
    expect(getDefaultAudienceForRole(undefined)).toBe('public')
    expect(getDefaultAudienceForRole(null)).toBe('public')
  })
})
