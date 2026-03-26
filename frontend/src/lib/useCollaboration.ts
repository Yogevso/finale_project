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
import { getReconnectDelay } from '@/lib/collaborationReconnect'
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
  persistenceWarning: string | null
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
const DEFAULT_AUTO_SAVE_INTERVAL = 5 * 60 * 1000 // 5 minutes
const COLLAB_TOKEN_REFRESH_INTERVAL_MS = 45 * 60 * 1000
const COLLAB_ACCESS_RECHECK_INTERVAL_MS = 5 * 60 * 1000
const COLLAB_ACCESS_REVOKED_MESSAGE =
  'Your collaboration access is no longer valid. Live editing has been disconnected.'

type CollabServerStatelessMessage =
  | {
      type: 'persistence_failed'
      message: string
    }
  | {
      type: 'persistence_restored'
    }

function parseCollabServerStatelessMessage(payload: string): CollabServerStatelessMessage | null {
  try {
    const parsed = JSON.parse(payload)
    if (!parsed || typeof parsed !== 'object' || typeof parsed.type !== 'string') {
      return null
    }

    if (parsed.type === 'persistence_failed' && typeof parsed.message === 'string') {
      return {
        type: 'persistence_failed',
        message: parsed.message,
      }
    }

    if (parsed.type === 'persistence_restored') {
      return {
        type: 'persistence_restored',
      }
    }
  } catch {
    return null
  }

  return null
}

function getHttpStatusCode(error: unknown): number | null {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof error.response === 'object' &&
    error.response !== null &&
    'status' in error.response &&
    typeof error.response.status === 'number'
  ) {
    return error.response.status
  }

  return null
}

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
    persistenceWarning: null,
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
  const accessRecheckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const suppressNextAutoReconnectRef = useRef(false)
  const pendingDisconnectReasonRef = useRef<string | null>(null)
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

  const flushCollaborationSessionEnd = useCallback(async () => {
    if (!sessionIdRef.current) {
      return
    }

    const sessionId = sessionIdRef.current
    const editsCount = editsCountRef.current
    sessionIdRef.current = null

    try {
      await api.endCollaborationSession(sessionId, editsCount)
    } catch (err) {
      console.error('Failed to end collaboration session:', err)
    }
  }, [])

  const applyCollabAuthResponse = useCallback((tokenResponse: {
    token: string
    permissions?: string[]
  }) => {
    const permissions = tokenResponse.permissions || []
    const isReadOnly = !permissions.includes('write')

    tokenRef.current = tokenResponse.token
    permissionsRef.current = permissions

    setState((prev) => ({
      ...prev,
      permissions,
      isReadOnly,
    }))

    onPermissionChangeRef.current?.(permissions, isReadOnly)
  }, [])

  const fetchCollabAuthResponse = useCallback(async () => {
    const tokenResponse = await api.getCollabToken(documentId)
    applyCollabAuthResponse(tokenResponse)
    return tokenResponse
  }, [applyCollabAuthResponse, documentId])

  const reconnectProviderWithFreshToken = useCallback(async () => {
    const provider = providerRef.current
    if (!provider || !connectionStateRef.current.isConnected) {
      return
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    reconnectAttemptRef.current = 0
    applyConnectionEvent({ type: 'RECONNECT_RESET' })

    suppressNextAutoReconnectRef.current = true
    try {
      provider.disconnect()
      await provider.connect()
    } catch (error) {
      suppressNextAutoReconnectRef.current = false
      throw error
    }
  }, [applyConnectionEvent])

  const disconnectForAccessLoss = useCallback((message: string) => {
    pendingDisconnectReasonRef.current = message
    permissionsRef.current = []

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    reconnectAttemptRef.current = 0
    suppressNextAutoReconnectRef.current = true
    setState((prev) => ({
      ...prev,
      permissions: [],
      isReadOnly: true,
      persistenceWarning: null,
    }))
    onErrorRef.current?.(new Error(message))
    providerRef.current?.disconnect()
  }, [])

  // Schedule a reconnection attempt with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    reconnectAttemptRef.current += 1
    const attempt = reconnectAttemptRef.current

    // L-09: add jitter to reduce reconnect stampedes after shared outages.
    const delay = getReconnectDelay(attempt)

    applyConnectionEvent({
      type: 'RECONNECT_SCHEDULED',
      attempt,
      delayMs: delay,
      maxAttempts: maxReconnectAttempts,
    })

    reconnectTimeoutRef.current = setTimeout(async () => {
      if (providerRef.current) {
        // M-15: Fetch a fresh collab token before reconnecting to avoid stale token reuse.
        try {
          await fetchCollabAuthResponse()
        } catch (error) {
          const statusCode = getHttpStatusCode(error)
          if (statusCode === 401 || statusCode === 403) {
            disconnectForAccessLoss(COLLAB_ACCESS_REVOKED_MESSAGE)
            return
          }
          // Still attempt reconnect with existing token as fallback
        }
        providerRef.current.connect()
      }
    }, delay)
  }, [applyConnectionEvent, disconnectForAccessLoss, fetchCollabAuthResponse, maxReconnectAttempts])

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
      const tokenResponse = await fetchCollabAuthResponse()

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
        if (origin !== providerRef.current && permissionsRef.current.includes('write')) {
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
        token: () => tokenRef.current ?? '',
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
          const suppressAutoReconnect = suppressNextAutoReconnectRef.current
          suppressNextAutoReconnectRef.current = false
          const disconnectReason = pendingDisconnectReasonRef.current
          pendingDisconnectReasonRef.current = null
          applyConnectionEvent({ type: 'DISCONNECTED' })
          void flushCollaborationSessionEnd()

          // Attempt auto-reconnect if enabled and not offline
          if (
            autoReconnect &&
            !connectionStateRef.current.isOffline &&
            reconnectAttemptRef.current < maxReconnectAttempts &&
            !suppressAutoReconnect
          ) {
            scheduleReconnect()
          }
          // Update global store
          setSession(documentId, {
            isConnected: false,
            isSynced: false,
          })
          if (disconnectReason) {
            setState((prev) => ({
              ...prev,
              error: disconnectReason,
              permissions: [],
              isReadOnly: true,
              persistenceWarning: null,
            }))
          }
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
        onStateless: ({ payload }) => {
          const message = parseCollabServerStatelessMessage(payload)
          if (!message) {
            return
          }

          if (message.type === 'persistence_failed') {
            setState((prev) => ({
              ...prev,
              persistenceWarning: message.message,
            }))
            onErrorRef.current?.(new Error(message.message))
            return
          }

          setState((prev) => ({
            ...prev,
            persistenceWarning: null,
          }))
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
      applyCollabAuthResponse,
      fetchCollabAuthResponse,
      flushCollaborationSessionEnd,
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

  useEffect(() => {
    const handlePageHide = () => {
      void flushCollaborationSessionEnd()
    }

    window.addEventListener('pagehide', handlePageHide)
    return () => {
      window.removeEventListener('pagehide', handlePageHide)
    }
  }, [flushCollaborationSessionEnd])

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

    try {
      await fetchCollabAuthResponse()
    } catch (error) {
      const statusCode = getHttpStatusCode(error)
      if (statusCode === 401 || statusCode === 403) {
        disconnectForAccessLoss(COLLAB_ACCESS_REVOKED_MESSAGE)
        return
      }

      const err = error instanceof Error ? error : new Error('Failed to reconnect')
      applyConnectionEvent({
        type: 'CONNECT_FAILED',
        error: err.message,
      })
      onErrorRef.current?.(err)
      return
    }

    if (providerRef.current) {
      providerRef.current.connect()
    } else {
      await connect()
    }
  }, [applyConnectionEvent, connect, disconnectForAccessLoss, fetchCollabAuthResponse])

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
    if (tokenRefreshIntervalRef.current) {
      clearInterval(tokenRefreshIntervalRef.current)
      tokenRefreshIntervalRef.current = null
    }
    if (accessRecheckIntervalRef.current) {
      clearInterval(accessRecheckIntervalRef.current)
      accessRecheckIntervalRef.current = null
    }

    void flushCollaborationSessionEnd()

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
      persistenceWarning: null,
      collaborators: [],
      provider: null,
      ydoc: null,
    })
  }, [documentId, flushCollaborationSessionEnd, removeSession])

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
      await fetchCollabAuthResponse()

      // Re-authenticate the live websocket so the collab server uses the fresh token.
      await reconnectProviderWithFreshToken()
    } catch (error) {
      const statusCode = getHttpStatusCode(error)
      if (statusCode === 401 || statusCode === 403) {
        disconnectForAccessLoss(COLLAB_ACCESS_REVOKED_MESSAGE)
        return
      }
      console.error('Failed to refresh permissions:', error)
    }
  }, [disconnectForAccessLoss, fetchCollabAuthResponse, reconnectProviderWithFreshToken])

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
          await fetchCollabAuthResponse()
          await reconnectProviderWithFreshToken()
        } catch (error) {
          const statusCode = getHttpStatusCode(error)
          if (statusCode === 401 || statusCode === 403) {
            disconnectForAccessLoss(COLLAB_ACCESS_REVOKED_MESSAGE)
            return
          }
          console.error('Collab token refresh failed:', error)
        }
      }, COLLAB_TOKEN_REFRESH_INTERVAL_MS)

      return () => {
        if (tokenRefreshIntervalRef.current) {
          clearInterval(tokenRefreshIntervalRef.current)
          tokenRefreshIntervalRef.current = null
        }
      }
    }
  }, [disconnectForAccessLoss, fetchCollabAuthResponse, reconnectProviderWithFreshToken, state.isConnected])

  // Re-check edit access regularly so revoked users are disconnected within 5 minutes.
  useEffect(() => {
    if (state.isConnected) {
      if (accessRecheckIntervalRef.current) {
        clearInterval(accessRecheckIntervalRef.current)
      }
      accessRecheckIntervalRef.current = setInterval(async () => {
        try {
          await fetchCollabAuthResponse()
        } catch (error) {
          const statusCode = getHttpStatusCode(error)
          if (statusCode === 401 || statusCode === 403) {
            disconnectForAccessLoss(COLLAB_ACCESS_REVOKED_MESSAGE)
            return
          }
          console.error('Collab access re-check failed:', error)
        }
      }, COLLAB_ACCESS_RECHECK_INTERVAL_MS)

      return () => {
        if (accessRecheckIntervalRef.current) {
          clearInterval(accessRecheckIntervalRef.current)
          accessRecheckIntervalRef.current = null
        }
      }
    }
  }, [disconnectForAccessLoss, fetchCollabAuthResponse, state.isConnected])

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
      void disconnectActionRef.current?.()
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
      if (accessRecheckIntervalRef.current) {
        clearInterval(accessRecheckIntervalRef.current)
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
