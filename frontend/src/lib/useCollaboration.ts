/**
 * useCollaboration Hook
 *
 * Manages real-time collaboration state using Yjs and Hocuspocus.
 * Handles WebSocket connection, document sync, and user presence.
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import * as Y from 'yjs'
import { HocuspocusProvider } from '@hocuspocus/provider'
import { IndexeddbPersistence } from 'y-indexeddb'
import {
  createInitialCollaborationConnectionState,
  toCollaborationConnectionFlags,
  transitionCollaborationConnectionState,
  type CollaborationConnectionMachineEvent,
} from '@/features/collaboration'
import { api } from '@/lib/api'
import { getUserColor } from '@/lib/userColors'
import { useCollaborationStore } from '@/stores/collaborationStore'

export interface CollaboratorInfo {
  clientId: number
  userId: string
  username: string
  color: string
  cursor?: {
    anchor: number
    head: number
  }
}

export interface CollaborationState {
  isConnected: boolean
  isConnecting: boolean
  isSynced: boolean
  isOffline: boolean
  isReadOnly: boolean
  hasLocalChanges: boolean
  reconnectAttempt: number
  permissions: string[]
  error: string | null
  collaborators: CollaboratorInfo[]
  provider: HocuspocusProvider | null
  ydoc: Y.Doc | null
}

export interface UseCollaborationOptions {
  documentId: number
  documentTitle?: string
  username: string
  userId: string | number
  enabled?: boolean
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  autoSaveInterval?: number  // Auto-snapshot interval in milliseconds (default: 5 min)
  onConnect?: () => void
  onDisconnect?: () => void
  onSynced?: () => void
  onError?: (error: Error) => void
  onOfflineChange?: (isOffline: boolean) => void
  onPermissionChange?: (permissions: string[], isReadOnly: boolean) => void
}

export interface UseCollaborationReturn extends CollaborationState {
  connect: () => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  getFragment: (name?: string) => Y.XmlFragment | null
  clearLocalData: () => Promise<void>
  refreshPermissions: () => Promise<void>
  canEdit: () => boolean
  createSnapshot: (name?: string) => Promise<void>
  sessionId: string | null
}

const COLLAB_SERVER_URL_FALLBACK = import.meta.env.VITE_COLLAB_SERVER_URL || 'ws://localhost:8002'
const MAX_RECONNECT_ATTEMPTS = 10
const BASE_RECONNECT_DELAY = 1000 // 1 second
const DEFAULT_AUTO_SAVE_INTERVAL = 5 * 60 * 1000 // 5 minutes

export function useCollaboration({
  documentId,
  documentTitle = '',
  username,
  userId,
  enabled = true,
  autoReconnect = true,
  maxReconnectAttempts = MAX_RECONNECT_ATTEMPTS,
  autoSaveInterval = DEFAULT_AUTO_SAVE_INTERVAL,
  onConnect,
  onDisconnect,
  onSynced,
  onError,
  onOfflineChange,
  onPermissionChange,
}: UseCollaborationOptions): UseCollaborationReturn {
  const initialConnectionState = createInitialCollaborationConnectionState(!navigator.onLine)
  const [state, setState] = useState<CollaborationState>({
    ...toCollaborationConnectionFlags(initialConnectionState),
    isReadOnly: false,
    hasLocalChanges: false,
    permissions: [],
    collaborators: [],
    provider: null,
    ydoc: null,
  })

  // Collaboration store for global state
  const setSession = useCollaborationStore((s) => s.setSession)
  const removeSession = useCollaborationStore((s) => s.removeSession)
  const updateCollaborators = useCollaborationStore((s) => s.updateCollaborators)

  const providerRef = useRef<HocuspocusProvider | null>(null)
  const ydocRef = useRef<Y.Doc | null>(null)
  const indexeddbRef = useRef<IndexeddbPersistence | null>(null)
  const tokenRef = useRef<string | null>(null)
  const permissionsRef = useRef<string[]>([])
  const sessionIdRef = useRef<string | null>(null)
  const editsCountRef = useRef<number>(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const autoSaveIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const tokenRefreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const connectionMachineStateRef = useRef(initialConnectionState)
  const initialConnectionFlags = toCollaborationConnectionFlags(initialConnectionState)
  const connectionStateRef = useRef({
    isConnected: initialConnectionFlags.isConnected,
    isConnecting: initialConnectionFlags.isConnecting,
    isOffline: initialConnectionFlags.isOffline,
  })
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)
  const onSyncedRef = useRef(onSynced)
  const onErrorRef = useRef(onError)
  const onOfflineChangeRef = useRef(onOfflineChange)
  const onPermissionChangeRef = useRef(onPermissionChange)
  const connectActionRef = useRef<(() => Promise<void>) | null>(null)
  const disconnectActionRef = useRef<(() => void) | null>(null)

  const applyConnectionEvent = useCallback((event: CollaborationConnectionMachineEvent) => {
    const nextConnectionState = transitionCollaborationConnectionState(
      connectionMachineStateRef.current,
      event,
    )
    connectionMachineStateRef.current = nextConnectionState
    const connectionFlags = toCollaborationConnectionFlags(nextConnectionState)

    connectionStateRef.current = {
      isConnected: connectionFlags.isConnected,
      isConnecting: connectionFlags.isConnecting,
      isOffline: connectionFlags.isOffline,
    }

    setState((prev) => ({
      ...prev,
      ...connectionFlags,
    }))
  }, [])

  useEffect(() => {
    connectionStateRef.current = {
      isConnected: state.isConnected,
      isConnecting: state.isConnecting,
      isOffline: state.isOffline,
    }
  }, [state.isConnected, state.isConnecting, state.isOffline])

  useEffect(() => {
    onConnectRef.current = onConnect
  }, [onConnect])

  useEffect(() => {
    onDisconnectRef.current = onDisconnect
  }, [onDisconnect])

  useEffect(() => {
    onSyncedRef.current = onSynced
  }, [onSynced])

  useEffect(() => {
    onErrorRef.current = onError
  }, [onError])

  useEffect(() => {
    onOfflineChangeRef.current = onOfflineChange
  }, [onOfflineChange])

  useEffect(() => {
    onPermissionChangeRef.current = onPermissionChange
  }, [onPermissionChange])

  // Get user color
  const userColor = getUserColor(userId)

  // Schedule a reconnection attempt with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    reconnectAttemptRef.current += 1
    const attempt = reconnectAttemptRef.current

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
    const delay = Math.min(BASE_RECONNECT_DELAY * Math.pow(2, attempt - 1), 30000)

    applyConnectionEvent({
      type: 'RECONNECT_SCHEDULED',
      attempt,
      delayMs: delay,
      maxAttempts: maxReconnectAttempts,
    })

    reconnectTimeoutRef.current = setTimeout(() => {
      if (providerRef.current) {
        providerRef.current.connect()
      }
    }, delay)
  }, [applyConnectionEvent, maxReconnectAttempts])

  // Connect to collaboration server
  const connect = useCallback(async () => {
    if (
      !enabled ||
      connectionStateRef.current.isConnecting ||
      connectionStateRef.current.isConnected
    ) {
      return
    }

    applyConnectionEvent({ type: 'CONNECT_REQUESTED' })

    try {
      // Get collaboration token from backend
      const tokenResponse = await api.getCollabToken(documentId)
      tokenRef.current = tokenResponse.token

      // Store permissions from token response
      const permissions = tokenResponse.permissions || []
      const isReadOnly = !permissions.includes('write')
      permissionsRef.current = permissions

      setState((prev) => ({
        ...prev,
        permissions,
        isReadOnly,
      }))

      // Notify about permission state
      onPermissionChangeRef.current?.(permissions, isReadOnly)

      // Create Yjs document
      const ydoc = new Y.Doc()
      ydocRef.current = ydoc

      // Set up IndexedDB persistence for offline support
      const indexeddbProvider = new IndexeddbPersistence(`doc-${documentId}`, ydoc)
      indexeddbRef.current = indexeddbProvider

      // Track when IndexedDB has synced (local data loaded)
      indexeddbProvider.on('synced', () => {
        setState((prev) => ({ ...prev, hasLocalChanges: false }))
      })

      // Track local changes (edits made while potentially offline) - only if not read-only
      ydoc.on('update', (_update: Uint8Array, origin: unknown) => {
        // If the update is local (not from the server), mark as having local changes
        if (origin !== providerRef.current && !isReadOnly) {
          setState((prev) => ({ ...prev, hasLocalChanges: true }))
          // Increment edits count for session tracking
          editsCountRef.current += 1
        }
      })

      // H-22: Derive collab server URL from backend response (single source of truth).
      // The backend returns a full websocket_url like ws://host:port/document/{id}.
      // Extract the base URL by stripping the /document/{id} suffix.
      let collabServerUrl = COLLAB_SERVER_URL_FALLBACK
      if (tokenResponse.websocket_url) {
        const docPathIdx = tokenResponse.websocket_url.lastIndexOf('/document/')
        if (docPathIdx !== -1) {
          collabServerUrl = tokenResponse.websocket_url.substring(0, docPathIdx)
        }
      }

      // Create Hocuspocus provider
      const provider = new HocuspocusProvider({
        url: collabServerUrl,
        name: `document/${documentId}`,
        document: ydoc,
        token: tokenResponse.token,
        onConnect: () => {
          // Reset reconnect counter on successful connection
          reconnectAttemptRef.current = 0
          editsCountRef.current = 0
          applyConnectionEvent({ type: 'CONNECT_SUCCEEDED' })
          // Update global store
          setSession(documentId, {
            documentTitle,
            isConnected: true,
          })
          // Start activity tracking session
          api.startCollaborationSession(documentId)
            .then((response) => {
              sessionIdRef.current = response.session_id
            })
            .catch((err) => {
              console.error('Failed to start collaboration session:', err)
            })
          onConnectRef.current?.()
        },
        onDisconnect: () => {
          applyConnectionEvent({ type: 'DISCONNECTED' })
          // End activity tracking session
          if (sessionIdRef.current) {
            api.endCollaborationSession(sessionIdRef.current, editsCountRef.current)
              .catch((err) => {
                console.error('Failed to end collaboration session:', err)
              })
            sessionIdRef.current = null
          }

          // Attempt auto-reconnect if enabled and not offline
          if (
            autoReconnect &&
            !connectionStateRef.current.isOffline &&
            reconnectAttemptRef.current < maxReconnectAttempts
          ) {
            scheduleReconnect()
          }
          // Update global store
          setSession(documentId, {
            isConnected: false,
            isSynced: false,
          })
          onDisconnectRef.current?.()
        },
        onSynced: () => {
          applyConnectionEvent({ type: 'SYNCED' })
          // Update global store
          setSession(documentId, { isSynced: true })
          onSyncedRef.current?.()
        },
        onAwarenessUpdate: ({ states }) => {
          const collaborators: CollaboratorInfo[] = []

          states.forEach((state, clientId) => {
            if (state.user) {
              collaborators.push({
                clientId,
                userId: state.user.userId || state.user.id,
                username: state.user.username || state.user.name,
                color: state.user.color || getUserColor(state.user.userId || clientId).color,
                cursor: state.cursor,
              })
            }
          })

          setState((prev) => ({ ...prev, collaborators }))
          // Update global store with join/leave detection
          updateCollaborators(documentId, collaborators)
        },
        onAuthenticationFailed: ({ reason }) => {
          const error = new Error(`Authentication failed: ${reason}`)
          applyConnectionEvent({
            type: 'CONNECT_FAILED',
            error: error.message,
          })
          onErrorRef.current?.(error)
        },
      })

      providerRef.current = provider

      // Set local awareness state
      provider.setAwarenessField('user', {
        userId: String(userId),
        username,
        color: userColor.color,
      })

      setState((prev) => ({
        ...prev,
        provider,
        ydoc,
      }))
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to connect')
      applyConnectionEvent({
        type: 'CONNECT_FAILED',
        error: err.message,
      })
      onErrorRef.current?.(err)
    }
  }, [
    applyConnectionEvent,
    autoReconnect,
    documentId,
    documentTitle,
    enabled,
    maxReconnectAttempts,
    scheduleReconnect,
    setSession,
    updateCollaborators,
    userColor.color,
    userId,
    username,
  ])

  // Track browser online/offline status
  useEffect(() => {
    const handleOnline = () => {
      applyConnectionEvent({ type: 'ONLINE' })
      onOfflineChangeRef.current?.(false)
      if (
        autoReconnect &&
        !connectionStateRef.current.isConnected &&
        !connectionStateRef.current.isConnecting
      ) {
        reconnectAttemptRef.current = 0
        void connectActionRef.current?.()
      }
    }

    const handleOffline = () => {
      applyConnectionEvent({ type: 'OFFLINE' })
      onOfflineChangeRef.current?.(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [applyConnectionEvent, autoReconnect])

  // Manual reconnect function
  const reconnect = useCallback(async () => {
    // Clear any scheduled reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Reset attempt counter
    reconnectAttemptRef.current = 0
    applyConnectionEvent({ type: 'RECONNECT_RESET' })

    // If we have a provider, try to reconnect it
    if (providerRef.current) {
      providerRef.current.connect()
    } else {
      // Otherwise, do a full connect
      await connect()
    }
  }, [applyConnectionEvent, connect])

  // Disconnect from collaboration server
  const disconnect = useCallback(() => {
    // Clear any scheduled reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (autoSaveIntervalRef.current) {
      clearInterval(autoSaveIntervalRef.current)
      autoSaveIntervalRef.current = null
    }

    // End activity tracking session before disconnecting
    if (sessionIdRef.current) {
      api.endCollaborationSession(sessionIdRef.current, editsCountRef.current)
        .catch((err) => {
          console.error('Failed to end collaboration session:', err)
        })
      sessionIdRef.current = null
    }

    if (providerRef.current) {
      providerRef.current.destroy()
      providerRef.current = null
    }

    if (indexeddbRef.current) {
      indexeddbRef.current.destroy()
      indexeddbRef.current = null
    }

    if (ydocRef.current) {
      ydocRef.current.destroy()
      ydocRef.current = null
    }

    tokenRef.current = null
    editsCountRef.current = 0

    // Remove from global store
    removeSession(documentId)

    const resetConnectionState = transitionCollaborationConnectionState(
      connectionMachineStateRef.current,
      {
        type: 'RESET',
        isOffline: !navigator.onLine,
      },
    )
    connectionMachineStateRef.current = resetConnectionState
    const resetConnectionFlags = toCollaborationConnectionFlags(resetConnectionState)
    connectionStateRef.current = {
      isConnected: resetConnectionFlags.isConnected,
      isConnecting: resetConnectionFlags.isConnecting,
      isOffline: resetConnectionFlags.isOffline,
    }

    setState({
      ...resetConnectionFlags,
      isReadOnly: false,
      hasLocalChanges: false,
      permissions: [],
      collaborators: [],
      provider: null,
      ydoc: null,
    })
  }, [documentId, removeSession])

  useEffect(() => {
    connectActionRef.current = connect
  }, [connect])

  useEffect(() => {
    disconnectActionRef.current = disconnect
  }, [disconnect])

  // Clear local IndexedDB data for this document
  const clearLocalData = useCallback(async () => {
    // Delete IndexedDB database for this document
    return new Promise<void>((resolve, reject) => {
      const request = indexedDB.deleteDatabase(`doc-${documentId}`)
      request.onsuccess = () => {
        setState((prev) => ({ ...prev, hasLocalChanges: false }))
        resolve()
      }
      request.onerror = () => reject(request.error)
    })
  }, [documentId])

  // Get XML fragment for TipTap
  const getFragment = useCallback((name = 'default'): Y.XmlFragment | null => {
    if (!ydocRef.current) return null
    return ydocRef.current.getXmlFragment(name)
  }, [])

  // Refresh permissions from the backend
  const refreshPermissions = useCallback(async () => {
    try {
      const tokenResponse = await api.getCollabToken(documentId)
      const permissions = tokenResponse.permissions || []
      const isReadOnly = !permissions.includes('write')

      permissionsRef.current = permissions
      tokenRef.current = tokenResponse.token

      setState((prev) => ({
        ...prev,
        permissions,
        isReadOnly,
      }))

      onPermissionChangeRef.current?.(permissions, isReadOnly)

      // If we're connected and permissions changed, we may need to reconnect
      // to update the Hocuspocus connection's read-only state
      if (providerRef.current && connectionStateRef.current.isConnected) {
        // Destroy and reconnect with new token
        providerRef.current.destroy()
        providerRef.current = null
        await connect()
      }
    } catch (error) {
      console.error('Failed to refresh permissions:', error)
    }
  }, [documentId, connect])

  // Check if user can edit
  const canEdit = useCallback(() => {
    return permissionsRef.current.includes('write')
  }, [])

  // Create a manual snapshot
  const createSnapshot = useCallback(async (name?: string) => {
    if (!sessionIdRef.current) {
      console.warn('Cannot create snapshot: No active session')
      return
    }
    try {
      await api.createSnapshot(documentId, {
        name,
        session_id: sessionIdRef.current,
      })
    } catch (error) {
      console.error('Failed to create snapshot:', error)
    }
  }, [documentId])

  // Set up auto-save interval when connected
  useEffect(() => {
    if (state.isConnected && autoSaveInterval > 0 && canEdit()) {
      // Clear existing interval
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current)
      }

      // Start new auto-save interval
      autoSaveIntervalRef.current = setInterval(async () => {
        if (sessionIdRef.current && editsCountRef.current > 0) {
          try {
            await api.createAutoSnapshot(documentId, sessionIdRef.current)
          } catch (error) {
            console.error('Auto-save snapshot failed:', error)
          }
        }
      }, autoSaveInterval)

      return () => {
        if (autoSaveIntervalRef.current) {
          clearInterval(autoSaveIntervalRef.current)
          autoSaveIntervalRef.current = null
        }
      }
    }
  }, [autoSaveInterval, canEdit, documentId, state.isConnected])

  // M-21: Refresh collab token periodically for long edit sessions (45 min < 1h expiry)
  useEffect(() => {
    if (state.isConnected) {
      if (tokenRefreshIntervalRef.current) {
        clearInterval(tokenRefreshIntervalRef.current)
      }
      tokenRefreshIntervalRef.current = setInterval(async () => {
        try {
          const tokenResponse = await api.getCollabToken(documentId)
          tokenRef.current = tokenResponse.token
          permissionsRef.current = tokenResponse.permissions || []
        } catch (error) {
          console.error('Collab token refresh failed:', error)
        }
      }, 45 * 60 * 1000) // 45 minutes

      return () => {
        if (tokenRefreshIntervalRef.current) {
          clearInterval(tokenRefreshIntervalRef.current)
          tokenRefreshIntervalRef.current = null
        }
      }
    }
  }, [documentId, state.isConnected])

  // Auto-connect when enabled
  useEffect(() => {
    if (
      enabled &&
      !connectionStateRef.current.isConnected &&
      !connectionStateRef.current.isConnecting
    ) {
      void connectActionRef.current?.()
    }

    return () => {
      disconnectActionRef.current?.()
    }
  }, [documentId, enabled])

  // Update awareness when user info changes
  useEffect(() => {
    if (providerRef.current) {
      providerRef.current.setAwarenessField('user', {
        userId: String(userId),
        username,
        color: userColor.color,
      })
    }
  }, [userId, username, userColor.color])

  // Cleanup reconnect timeout and auto-save interval on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current)
      }
      if (tokenRefreshIntervalRef.current) {
        clearInterval(tokenRefreshIntervalRef.current)
      }
    }
  }, [])

  return {
    ...state,
    connect,
    disconnect,
    reconnect,
    getFragment,
    clearLocalData,
    refreshPermissions,
    canEdit,
    createSnapshot,
    sessionId: sessionIdRef.current,
  }
}

export default useCollaboration
