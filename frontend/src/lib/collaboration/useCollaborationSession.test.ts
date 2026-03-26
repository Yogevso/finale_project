import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useCollaborationSession } from './useCollaborationSession'

describe('useCollaborationSession', () => {
  it('flushes the active collaboration session on pagehide', async () => {
    const startCollaborationSession = vi.fn().mockResolvedValue({ session_id: 'session-1' })
    const endCollaborationSession = vi.fn().mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      useCollaborationSession({
        documentId: 101,
        documentTitle: 'Doc',
        autoSaveInterval: 0,
        isConnected: false,
        canEdit: true,
        setSession: vi.fn(),
        startCollaborationSession,
        endCollaborationSession,
        createSnapshotApi: vi.fn(),
        createAutoSnapshot: vi.fn(),
      }),
    )

    act(() => {
      result.current.handleProviderConnected()
    })

    await waitFor(() =>
      expect(result.current.sessionIdRef.current).toBe('session-1'),
    )

    act(() => {
      window.dispatchEvent(new Event('pagehide'))
    })

    await waitFor(() =>
      expect(endCollaborationSession).toHaveBeenCalledWith('session-1', 0),
    )
  })

  it('creates auto snapshots for edited sessions on the configured interval', async () => {
    const createAutoSnapshot = vi.fn().mockResolvedValue({ created: true })
    const startCollaborationSession = vi.fn().mockResolvedValue({ session_id: 'session-2' })
    const endCollaborationSession = vi.fn().mockResolvedValue(undefined)
    const setSession = vi.fn()
    const intervalCallbacks: Array<() => void | Promise<void>> = []

    const setIntervalSpy = vi
      .spyOn(globalThis, 'setInterval')
      .mockImplementation(((callback: TimerHandler) => {
        intervalCallbacks.push(callback as () => void | Promise<void>)
        return 1 as unknown as ReturnType<typeof setInterval>
      }) as unknown as typeof setInterval)
    const clearIntervalSpy = vi
      .spyOn(globalThis, 'clearInterval')
      .mockImplementation((() => undefined) as unknown as typeof clearInterval)

    try {
      const { result, rerender } = renderHook(
        ({ isConnected }) =>
          useCollaborationSession({
            documentId: 202,
            documentTitle: 'Doc',
            autoSaveInterval: 5_000,
            isConnected,
            canEdit: true,
            setSession,
            startCollaborationSession,
            endCollaborationSession,
            createSnapshotApi: vi.fn(),
            createAutoSnapshot,
          }),
        { initialProps: { isConnected: false } },
      )

      await act(async () => {
        result.current.handleProviderConnected()
        await Promise.resolve()
      })

      await waitFor(() =>
        expect(result.current.sessionIdRef.current).toBe('session-2'),
      )

      act(() => {
        result.current.recordLocalEdit()
      })

      rerender({ isConnected: true })

      expect(intervalCallbacks.length).toBeGreaterThan(0)

      await act(async () => {
        const latestIntervalCallback = intervalCallbacks[intervalCallbacks.length - 1]
        await latestIntervalCallback?.()
      })

      expect(createAutoSnapshot).toHaveBeenCalledWith(202, 'session-2')
    } finally {
      setIntervalSpy.mockRestore()
      clearIntervalSpy.mockRestore()
    }
  })
})
