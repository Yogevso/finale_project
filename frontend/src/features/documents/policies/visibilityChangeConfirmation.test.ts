import { describe, expect, it } from 'vitest'

import {
  getVisibilityLabel,
  requiresVisibilityChangeConfirmation,
} from './visibilityChangeConfirmation'

describe('visibility change confirmation policy', () => {
  it('requires confirmation only for broader audience transitions', () => {
    expect(requiresVisibilityChangeConfirmation('internal', 'company')).toBe(true)
    expect(requiresVisibilityChangeConfirmation('internal', 'public')).toBe(true)
    expect(requiresVisibilityChangeConfirmation('company', 'public')).toBe(true)
    expect(requiresVisibilityChangeConfirmation('company', 'internal')).toBe(false)
    expect(requiresVisibilityChangeConfirmation('public', 'company')).toBe(false)
    expect(requiresVisibilityChangeConfirmation('internal', 'internal')).toBe(false)
  })

  it('provides display labels for visibility values', () => {
    expect(getVisibilityLabel('internal')).toBe('Internal')
    expect(getVisibilityLabel('company')).toBe('Company')
    expect(getVisibilityLabel('public')).toBe('Public')
  })
})
