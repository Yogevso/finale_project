import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCollaboration } from './useCollaboration'
import { buildDocumentDetailCollaborationScenario } from '@/test/scenarios/documentDetailScenario'

const shared = vi.hoisted(() => ({
  providerInstances: [] as Array<{
    options: {
      name: string
      token?: string | (() => string) | (() => Promise<string>)
      onConnect?: () => void
      onDisconnect?: () => void
      onStateless?: (data: { payload: string }) => void
    }
    connect: ReturnType<typeof vi.fn>
    disconnect: ReturnType<typeof vi.fn>
    destroy: ReturnType<typeof vi.fn>
    setConfiguration: ReturnType<typeof vi.fn>
  }>,
  getCollabToken: vi.fn(),
  startCollaborationSession: vi.fn(),
  endCollaborationSession: vi.fn(),
  setSession: vi.fn(),
  removeSession: vi.fn(),
  updateCollaborators: vi.fn(),
}))

vi.mock('@hocuspocus/provider', () => {
  class MockHocuspocusProvider {
    options: {
      name: string
      token?: string | (() => string) | (() => Promise<string>)
      onConnect?: () => void
      onDisconnect?: () => void
      onStateless?: (data: { payload: string }) => void
    }
    connect = vi.fn()
    disconnect = vi.fn()
    destroy = vi.fn()
    setConfiguration = vi.fn()
    setAwarenessField = vi.fn()

    constructor(options: {
      name: string
      token?: string | (() => string) | (() => Promise<string>)
      onConnect?: () => void
      onDisconnect?: () => void
      onStateless?: (data: { payload: string }) => void
    }) {
      this.options = options
      shared.providerInstances.push(this)
    }
  }

  return {
    HocuspocusProvider: MockHocuspocusProvider,
  }
})

vi.mock('yjs', () => {
  class MockYDoc {
    on = vi.fn()
    destroy = vi.fn()
    getXmlFragment = vi.fn(() => null)
  }

  return {
    Doc: MockYDoc,
  }
})

vi.mock('y-indexeddb', () => {
  class MockIndexeddbPersistence {
    on = vi.fn()
    destroy = vi.fn()

    constructor(_name: string, _doc: unknown) {}
  }

  return {
    IndexeddbPersistence: MockIndexeddbPersistence,
  }
})

vi.mock('@/lib/api', () => ({
  api: {
    getCollabToken: shared.getCollabToken,
    startCollaborationSession: shared.startCollaborationSession,
    endCollaborationSession: shared.endCollaborationSession,
    createSnapshot: vi.fn().mockResolvedValue(undefined),
    createAutoSnapshot: vi.fn().mockResolvedValue({ created: true }),
  },
}))

vi.mock('@/lib/userColors', () => ({
  getUserColor: vi.fn(() => ({ color: '#2563eb' })),
}))

vi.mock('@/stores/collaborationStore', () => ({
  useCollaborationStore: (selector: (state: unknown) => unknown) =>
    selector({
      setSession: shared.setSession,
      removeSession: shared.removeSession,
      updateCollaborators: shared.updateCollaborators,
    }),
}))

describe('useCollaboration', () => {
  beforeEach(() => {
    shared.providerInstances.splice(0, shared.providerInstances.length)
    shared.getCollabToken.mockReset()
    shared.startCollaborationSession.mockReset()
    shared.endCollaborationSession.mockReset()
    shared.setSession.mockReset()
    shared.removeSession.mockReset()
    shared.updateCollaborators.mockReset()

    shared.getCollabToken.mockImplementation(async (documentId: number) => {
      const scenario = buildDocumentDetailCollaborationScenario(documentId)
      return {
        ...scenario.collabToken,
        websocket_url: 'ws://localhost:8002',
      }
    })
    shared.startCollaborationSession.mockResolvedValue({ session_id: 'session-1' })
    shared.endCollaborationSession.mockResolvedValue(undefined)
  })

  it('tears down previous provider and reconnects when documentId changes', async () => {
    const { rerender, unmount } = renderHook(
      ({ documentId }) =>
        useCollaboration({
          documentId,
          username: 'tester',
          userId: 42,
          enabled: true,
          autoReconnect: false,
        }),
      { initialProps: { documentId: 101 } },
    )

    await waitFor(() => expect(shared.getCollabToken).toHaveBeenCalledWith(101))
    await waitFor(() => expect(shared.providerInstances).toHaveLength(1))
    expect(shared.providerInstances[0].options.name).toBe('document/101')

    rerender({ documentId: 202 })

    await waitFor(() => expect(shared.getCollabToken).toHaveBeenCalledWith(202))
    await waitFor(() => expect(shared.providerInstances).toHaveLength(2))
    expect(shared.providerInstances[1].options.name).toBe('document/202')
    expect(shared.providerInstances[0].destroy).toHaveBeenCalledTimes(1)
    expect(shared.removeSession).toHaveBeenCalledWith(101)

    unmount()
    expect(shared.providerInstances[1].destroy).toHaveBeenCalledTimes(1)
    expect(shared.removeSession).toHaveBeenCalledWith(202)
  })

  it('refreshes the live collaboration token by reconnecting the provider', async () => {
    const intervalCallbacks: Array<{
      callback: () => void | Promise<void>
      delay?: number
    }> = []
    let restoreTimerSpies: (() => void) | null = null
    shared.getCollabToken
      .mockResolvedValueOnce({
        token: 'token-initial',
        permissions: ['read', 'write'],
        websocket_url: 'ws://localhost:8002',
      })
      .mockResolvedValueOnce({
        token: 'token-refreshed',
        permissions: ['read', 'write'],
        websocket_url: 'ws://localhost:8002',
      })

    try {
      const { result, unmount } = renderHook(() =>
        useCollaboration({
          documentId: 303,
          username: 'tester',
          userId: 42,
          enabled: true,
          autoReconnect: false,
          autoSaveInterval: 0,
        }),
      )

      await waitFor(() => expect(shared.providerInstances).toHaveLength(1))
      const provider = shared.providerInstances[0]
      const setIntervalSpy = vi
        .spyOn(globalThis, 'setInterval')
        .mockImplementation(((callback: TimerHandler, delay?: number) => {
          intervalCallbacks.push({
            callback: callback as () => void | Promise<void>,
            delay,
          })
          return 1 as unknown as ReturnType<typeof setInterval>
        }) as unknown as typeof setInterval)
      const clearIntervalSpy = vi
        .spyOn(globalThis, 'clearInterval')
        .mockImplementation((() => undefined) as unknown as typeof clearInterval)
      restoreTimerSpies = () => {
        setIntervalSpy.mockRestore()
        clearIntervalSpy.mockRestore()
      }

      const initialTokenGetter = provider.options.token
      expect(typeof initialTokenGetter).toBe('function')
      if (typeof initialTokenGetter !== 'function') {
        throw new Error('Expected provider token to be a function')
      }
      const initialToken = await initialTokenGetter()
      expect(initialToken).toBe('token-initial')

      act(() => {
        provider.options.onConnect?.()
      })

      await act(async () => {
        await Promise.resolve()
      })
      expect(result.current.isConnected).toBe(true)
      await waitFor(() => expect(intervalCallbacks.length).toBeGreaterThan(0))

      const tokenRefreshCallback = intervalCallbacks.find(
        (interval) => interval.delay === 45 * 60 * 1000,
      )
      expect(tokenRefreshCallback).toBeDefined()

      await act(async () => {
        await tokenRefreshCallback?.callback()
      })

      expect(shared.getCollabToken).toHaveBeenCalledTimes(2)
      expect(provider.disconnect).toHaveBeenCalledTimes(1)
      expect(provider.connect).toHaveBeenCalledTimes(1)
      const refreshedTokenGetter = provider.options.token
      expect(typeof refreshedTokenGetter).toBe('function')
      if (typeof refreshedTokenGetter !== 'function') {
        throw new Error('Expected provider token to be a function')
      }
      const refreshedToken = await refreshedTokenGetter()
      expect(refreshedToken).toBe('token-refreshed')
      unmount()
    } finally {
      restoreTimerSpies?.()
    }
  })

  it('shows a persistence warning until the server confirms saving has recovered', async () => {
    const { result } = renderHook(() =>
      useCollaboration({
        documentId: 404,
        username: 'tester',
        userId: 42,
        enabled: true,
        autoReconnect: false,
        autoSaveInterval: 0,
      }),
    )

    await waitFor(() => expect(shared.providerInstances).toHaveLength(1))
    const provider = shared.providerInstances[0]

    act(() => {
      provider.options.onStateless?.({
        payload: JSON.stringify({
          type: 'persistence_failed',
          message:
            'Changes are no longer being saved to the server. Keep this tab open and reconnect before closing it.',
        }),
      })
    })

    expect(result.current.persistenceWarning).toBe(
      'Changes are no longer being saved to the server. Keep this tab open and reconnect before closing it.',
    )

    act(() => {
      provider.options.onStateless?.({
        payload: JSON.stringify({
          type: 'persistence_restored',
        }),
      })
    })

    expect(result.current.persistenceWarning).toBeNull()
  })

  it('flushes the collaboration session when the page is hidden', async () => {
    renderHook(() =>
      useCollaboration({
        documentId: 606,
        username: 'tester',
        userId: 42,
        enabled: true,
        autoReconnect: false,
        autoSaveInterval: 0,
      }),
    )

    await waitFor(() => expect(shared.providerInstances).toHaveLength(1))
    const provider = shared.providerInstances[0]

    await act(async () => {
      provider.options.onConnect?.()
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(shared.startCollaborationSession).toHaveBeenCalledWith(606)

    act(() => {
      window.dispatchEvent(new Event('pagehide'))
    })

    await waitFor(() =>
      expect(shared.endCollaborationSession).toHaveBeenCalledWith('session-1', 0),
    )
  })

  it('disconnects live editing within 5 minutes when collaboration access is revoked', async () => {
    const intervalCallbacks: Array<{
      callback: () => void | Promise<void>
      delay?: number
    }> = []
    let restoreTimerSpies: (() => void) | null = null
    shared.getCollabToken
      .mockResolvedValueOnce({
        token: 'token-initial',
        permissions: ['read', 'write'],
        websocket_url: 'ws://localhost:8002',
      })
      .mockRejectedValueOnce({
        response: {
          status: 403,
        },
      })

    try {
      const { result } = renderHook(() =>
        useCollaboration({
          documentId: 505,
          username: 'tester',
          userId: 42,
          enabled: true,
          autoReconnect: false,
          autoSaveInterval: 0,
        }),
      )

      await waitFor(() => expect(shared.providerInstances).toHaveLength(1))
      const provider = shared.providerInstances[0]
      const setIntervalSpy = vi
        .spyOn(globalThis, 'setInterval')
        .mockImplementation(((callback: TimerHandler, delay?: number) => {
          intervalCallbacks.push({
            callback: callback as () => void | Promise<void>,
            delay,
          })
          return 1 as unknown as ReturnType<typeof setInterval>
        }) as unknown as typeof setInterval)
      const clearIntervalSpy = vi
        .spyOn(globalThis, 'clearInterval')
        .mockImplementation((() => undefined) as unknown as typeof clearInterval)
      restoreTimerSpies = () => {
        setIntervalSpy.mockRestore()
        clearIntervalSpy.mockRestore()
      }

      act(() => {
        provider.options.onConnect?.()
      })

      await act(async () => {
        await Promise.resolve()
      })
      await waitFor(() =>
        expect(
          intervalCallbacks.some((interval) => interval.delay === 5 * 60 * 1000),
        ).toBe(true),
      )

      const accessRecheckCallback = intervalCallbacks.find(
        (interval) => interval.delay === 5 * 60 * 1000,
      )
      expect(accessRecheckCallback).toBeDefined()

      await act(async () => {
        await accessRecheckCallback?.callback()
      })

      expect(shared.getCollabToken).toHaveBeenCalledTimes(2)
      expect(provider.disconnect).toHaveBeenCalledTimes(1)

      act(() => {
        provider.options.onDisconnect?.()
      })

      expect(result.current.isConnected).toBe(false)
      expect(result.current.isReadOnly).toBe(true)
      expect(result.current.permissions).toEqual([])
      expect(result.current.error).toBe(
        'Your collaboration access is no longer valid. Live editing has been disconnected.',
      )
    } finally {
      restoreTimerSpies?.()
    }
  })
})
