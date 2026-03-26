import { describe, expect, it } from 'vitest'

import { getReconnectDelay } from './collaborationReconnect'

describe('collaborationReconnect', () => {
  it('adds jitter to the exponential reconnect delay', () => {
    expect(getReconnectDelay(1, 0)).toBe(800)
    expect(getReconnectDelay(1, 1)).toBe(1200)
    expect(getReconnectDelay(3, 0.5)).toBe(4000)
  })

  it('caps the jittered delay at the max reconnect delay', () => {
    expect(getReconnectDelay(8, 1)).toBe(30000)
  })
})
