import { describe, expect, it } from 'vitest'

import {
  createInitialCollaborationConnectionState,
  toCollaborationConnectionFlags,
  transitionCollaborationConnectionState,
} from './collaborationConnectionMachine'

describe('collaborationConnectionMachine', () => {
  it('moves through connect and sync transitions', () => {
    const initial = createInitialCollaborationConnectionState(false)
    const connecting = transitionCollaborationConnectionState(initial, { type: 'CONNECT_REQUESTED' })
    const connected = transitionCollaborationConnectionState(connecting, { type: 'CONNECT_SUCCEEDED' })
    const synced = transitionCollaborationConnectionState(connected, { type: 'SYNCED' })

    expect(connecting.phase).toBe('connecting')
    expect(connected.phase).toBe('connected')
    expect(synced.isSynced).toBe(true)
    expect(toCollaborationConnectionFlags(synced)).toEqual(
      expect.objectContaining({
        isConnected: true,
        isConnecting: false,
        isSynced: true,
      }),
    )
  })

  it('builds reconnect state with explicit attempt metadata', () => {
    const connected = transitionCollaborationConnectionState(
      createInitialCollaborationConnectionState(false),
      { type: 'CONNECT_SUCCEEDED' },
    )

    const reconnecting = transitionCollaborationConnectionState(connected, {
      type: 'RECONNECT_SCHEDULED',
      attempt: 3,
      delayMs: 4000,
      maxAttempts: 10,
    })

    expect(reconnecting.phase).toBe('reconnecting')
    expect(reconnecting.reconnectAttempt).toBe(3)
    expect(reconnecting.error).toContain('attempt 3/10')
  })

  it('goes to idle when offline event arrives', () => {
    const connected = transitionCollaborationConnectionState(
      createInitialCollaborationConnectionState(false),
      { type: 'CONNECT_SUCCEEDED' },
    )

    const offline = transitionCollaborationConnectionState(connected, { type: 'OFFLINE' })
    expect(offline.phase).toBe('idle')
    expect(offline.isOffline).toBe(true)
    expect(offline.isSynced).toBe(false)
  })
})

