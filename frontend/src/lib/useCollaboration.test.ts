import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCollaboration } from './useCollaboration'
import { buildDocumentDetailCollaborationScenario } from '@/test/scenarios/documentDetailScenario'

const shared = vi.hoisted(() => ({
  providerInstances: [] as Array<{
    options: { name: string }
    destroy: ReturnType<typeof vi.fn>
  }>,
  getCollabToken: vi.fn(),
  setSession: vi.fn(),
  removeSession: vi.fn(),
  updateCollaborators: vi.fn(),
}))

vi.mock('@hocuspocus/provider', () => {
  class MockHocuspocusProvider {
    options: { name: string }
    connect = vi.fn()
    destroy = vi.fn()
    setAwarenessField = vi.fn()

    constructor(options: { name: string }) {
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
    startCollaborationSession: vi.fn().mockResolvedValue({ session_id: 'session-1' }),
    endCollaborationSession: vi.fn().mockResolvedValue(undefined),
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
})
