import { describe, expect, it } from 'vitest'

import { parseBooleanFlag, resolveFrontendFeatureFlags } from './featureFlags'

describe('featureFlags', () => {
  it('parses boolean flag values safely', () => {
    expect(parseBooleanFlag('true', false)).toBe(true)
    expect(parseBooleanFlag('1', false)).toBe(true)
    expect(parseBooleanFlag('false', true)).toBe(false)
    expect(parseBooleanFlag('0', true)).toBe(false)
    expect(parseBooleanFlag(undefined, true)).toBe(true)
    expect(parseBooleanFlag('invalid', false)).toBe(false)
  })

  it('resolves optimistic concurrency flag from env', () => {
    expect(
      resolveFrontendFeatureFlags({
        VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS: 'false',
      }).optimisticConcurrencyHeaders,
    ).toBe(false)

    expect(
      resolveFrontendFeatureFlags({
        VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS: 'true',
      }).optimisticConcurrencyHeaders,
    ).toBe(true)
  })
})
