import { describe, expect, it } from 'vitest'

import { reviewStatusConfig } from './constants'

describe('reviews status config', () => {
  it('contains labels and styles for each review state', () => {
    expect(reviewStatusConfig.pending.label).toBe('Pending')
    expect(reviewStatusConfig.approved.className).toContain('emerald')
    expect(reviewStatusConfig.rejected.label).toBe('Rejected')
    expect(reviewStatusConfig.cancelled.className).toContain('slate')
  })
})

