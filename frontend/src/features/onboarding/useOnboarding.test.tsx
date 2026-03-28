import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useOnboarding } from './useOnboarding'

const getMyOnboardingStateMock = vi.fn()
const updateMyOnboardingStateMock = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getMyOnboardingState: (...args: unknown[]) => getMyOnboardingStateMock(...args),
    updateMyOnboardingState: (...args: unknown[]) => updateMyOnboardingStateMock(...args),
  },
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useOnboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens the guide automatically only after onboarding state loads as unseen', async () => {
    getMyOnboardingStateMock.mockResolvedValue({
      guide_version: 1,
      guide_seen_at: null,
      checklist_version: 1,
      completed_steps: [],
      checklist_completed_at: null,
    })

    const { result } = renderHook(() => useOnboarding('customer'), {
      wrapper: createWrapper(),
    })

    expect(result.current.shouldAutoOpenGuide).toBe(false)

    await waitFor(() => {
      expect(result.current.query.isSuccess).toBe(true)
    })

    expect(result.current.shouldAutoOpenGuide).toBe(true)
    expect(result.current.config?.checklistTitle).toContain('Customer')
  })

  it('normalizes stale checklist versions and persists toggled steps', async () => {
    getMyOnboardingStateMock.mockResolvedValue({
      guide_version: 1,
      guide_seen_at: '2026-03-28T08:00:00Z',
      checklist_version: 99,
      completed_steps: ['stale_step'],
      checklist_completed_at: '2026-03-28T09:00:00Z',
    })
    updateMyOnboardingStateMock.mockImplementation(async (payload) => ({
      guide_version: 1,
      guide_seen_at: '2026-03-28T08:00:00Z',
      checklist_version: payload.checklist_version ?? 1,
      completed_steps: payload.completed_steps ?? [],
      checklist_completed_at: payload.checklist_completed_at ?? null,
    }))

    const { result } = renderHook(() => useOnboarding('viewer'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.query.isSuccess).toBe(true)
    })

    expect(result.current.completedSteps).toEqual([])

    await act(async () => {
      await result.current.toggleChecklistStep('open_internal_documents')
    })

    expect(updateMyOnboardingStateMock).toHaveBeenCalled()
    expect(updateMyOnboardingStateMock.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        checklist_version: 1,
        completed_steps: ['open_internal_documents'],
      }),
    )
    await waitFor(() => {
      expect(result.current.completedSteps).toEqual(['open_internal_documents'])
    })
  })
})
