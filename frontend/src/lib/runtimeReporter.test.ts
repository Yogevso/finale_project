import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  reportRuntimeError,
  reportRuntimeWarning,
  resetRuntimeNotificationThrottle,
} from './runtimeReporter'

const shared = vi.hoisted(() => ({
  toast: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: Object.assign(shared.toast, {
    error: shared.toastError,
  }),
}))

describe('runtimeReporter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetRuntimeNotificationThrottle()
    delete (window as Window & { __ERROR_REPORTER__?: unknown }).__ERROR_REPORTER__
    delete (window as Window & { __RUNTIME_REPORTER__?: unknown }).__RUNTIME_REPORTER__
  })

  it('forwards runtime errors to console, toast, and external reporters', () => {
    const errorReporter = vi.fn()
    const runtimeReporter = vi.fn()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    ;(window as Window & { __ERROR_REPORTER__?: typeof errorReporter }).__ERROR_REPORTER__ =
      errorReporter
    ;(window as Window & { __RUNTIME_REPORTER__?: typeof runtimeReporter }).__RUNTIME_REPORTER__ =
      runtimeReporter

    try {
      reportRuntimeError({
        scope: 'preview.reader',
        message: 'Reader View retry failed',
        error: new Error('backend timeout'),
        userMessage: 'Please try again in a moment.',
        toastTitle: 'Reader View unavailable',
      })
    } finally {
      consoleSpy.mockRestore()
    }

    expect(shared.toastError).toHaveBeenCalledWith('Reader View unavailable', {
      description: 'Please try again in a moment.',
    })
    expect(errorReporter).toHaveBeenCalledTimes(1)
    expect(runtimeReporter).toHaveBeenCalledWith(
      expect.objectContaining({
        level: 'error',
        scope: 'preview.reader',
        message: 'Reader View retry failed',
        userMessage: 'Please try again in a moment.',
      }),
    )
  })

  it('deduplicates repeated warning toasts while keeping runtime events flowing', () => {
    const runtimeReporter = vi.fn()
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    ;(window as Window & { __RUNTIME_REPORTER__?: typeof runtimeReporter }).__RUNTIME_REPORTER__ =
      runtimeReporter

    try {
      reportRuntimeWarning({
        scope: 'collaboration.access',
        message: 'Failed to refresh permissions',
        error: new Error('network'),
        userMessage: 'Live editing will retry automatically.',
        toastTitle: 'Collaboration degraded',
        dedupeKey: 'collab-refresh',
      })
      reportRuntimeWarning({
        scope: 'collaboration.access',
        message: 'Failed to refresh permissions',
        error: new Error('network'),
        userMessage: 'Live editing will retry automatically.',
        toastTitle: 'Collaboration degraded',
        dedupeKey: 'collab-refresh',
      })
    } finally {
      consoleSpy.mockRestore()
    }

    expect(shared.toast).toHaveBeenCalledTimes(1)
    expect(runtimeReporter).toHaveBeenCalledTimes(2)
  })
})
