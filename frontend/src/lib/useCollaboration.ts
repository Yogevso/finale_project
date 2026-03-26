import { useCallback, useEffect, useRef, useState } from 'react'
import { HocuspocusProvider } from '@hocuspocus/provider'
import { IndexeddbPersistence } from 'y-indexeddb'
import * as Y from 'yjs'
import {
  createInitialCollaborationConnectionState,
  toCollaborationConnectionFlags,
  transitionCollaborationConnectionState,
  type CollaborationConnectionMachineEvent,
} from '@/features/collaboration'
import { useLatestValue } from '@/hooks/useLatestValue'
import { api } from '@/lib/api'
import { getUserColor } from '@/lib/userColors'
import { useCollaborationStore } from '@/stores/collaborationStore'
import {
  COLLAB_SERVER_URL_FALLBACK,
  COLLAB_ACCESS_REVOKED_MESSAGE,
  DEFAULT_AUTO_SAVE_INTERVAL,
  MAX_RECONNECT_ATTEMPTS,
  getHttpStatusCode,
} from './collaboration/collaborationRuntime'
import { establishCollaborationConnection } from './collaboration/connectCollaborationProvider'
import type {
  CollaborationState,
  UseCollaborationOptions,
  UseCollaborationReturn,
} from './collaboration/types'
import { useCollaborationAccess } from './collaboration/useCollaborationAccess'
import { useCollaborationNetworkLifecycle } from './collaboration/useCollaborationNetworkLifecycle'
import { useCollaborationSession } from './collaboration/useCollaborationSession'

export type {
  CollaborationAuthResponse,
  CollaborationState,
  CollaboratorInfo,
  UseCollaborationOptions,
  UseCollaborationReturn,
} from './collaboration/types'

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
  // H-22: the runtime fallback still comes from VITE_COLLAB_SERVER_URL via collaborationRuntime.
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

  const setSession = useCollaborationStore((store) => store.setSession)
  const removeSession = useCollaborationStore((store) => store.removeSession)
  const updateCollaborators = useCollaborationStore((store) => store.updateCollaborators)

  const providerRef = useRef<HocuspocusProvider | null>(null)
  const ydocRef = useRef<Y.Doc | null>(null)
  const indexeddbRef = useRef<IndexeddbPersistence | null>(null)
  const connectionMachineStateRef = useRef(initialConnectionState)
  const initialConnectionFlags = toCollaborationConnectionFlags(initialConnectionState)
  const connectionStateRef = useRef({
    isConnected: initialConnectionFlags.isConnected,
    isConnecting: initialConnectionFlags.isConnecting,
    isOffline: initialConnectionFlags.isOffline,
  })

  const onConnectRef = useLatestValue(onConnect)
  const onDisconnectRef = useLatestValue(onDisconnect)
  const onSyncedRef = useLatestValue(onSynced)
  const onErrorRef = useLatestValue(onError)
  const onOfflineChangeRef = useLatestValue(onOfflineChange)
  const onPermissionChangeRef = useLatestValue(onPermissionChange)

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

  const userColor = getUserColor(userId)

  const {
    tokenRef,
    permissionsRef,
    reconnectAttemptRef,
    suppressNextAutoReconnectRef,
    pendingDisconnectReasonRef,
    fetchCollabAuthResponse,
    disconnectForAccessLoss,
    scheduleReconnect,
    clearReconnectTimeout,
    clearBackgroundIntervals,
    resetReconnectMachine,
    resetAccessState,
    refreshPermissions,
    canEdit,
  } = useCollaborationAccess({
    documentId,
    isConnected: state.isConnected,
    maxReconnectAttempts,
    providerRef,
    connectionStateRef,
    setState,
    applyConnectionEvent,
    onErrorRef,
    onPermissionChangeRef,
    getCollabToken: api.getCollabToken,
  })

  const {
    sessionIdRef,
    flushCollaborationSessionEnd,
    handleProviderConnected,
    recordLocalEdit,
    resetSessionTracking,
    createSnapshot,
  } = useCollaborationSession({
    documentId,
    documentTitle,
    autoSaveInterval,
    isConnected: state.isConnected,
    canEdit: state.permissions.includes('write'),
    setSession,
    startCollaborationSession: api.startCollaborationSession,
    endCollaborationSession: api.endCollaborationSession,
    createSnapshotApi: api.createSnapshot,
    createAutoSnapshot: api.createAutoSnapshot,
  })

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
      await establishCollaborationConnection({
        documentId,
        username,
        userId,
        userColor: userColor.color,
        autoReconnect,
        maxReconnectAttempts,
        fetchCollabAuthResponse,
        tokenRef,
        permissionsRef,
        providerRef,
        ydocRef,
        indexeddbRef,
        reconnectAttemptRef,
        suppressNextAutoReconnectRef,
        pendingDisconnectReasonRef,
        connectionStateRef,
        setState,
        applyConnectionEvent,
        scheduleReconnect,
        setSession,
        updateCollaborators,
        handleProviderConnected,
        flushCollaborationSessionEnd,
        recordLocalEdit,
        onConnect: onConnectRef.current,
        onDisconnect: onDisconnectRef.current,
        onSynced: onSyncedRef.current,
        onError: onErrorRef.current,
        fallbackCollabServerUrl: COLLAB_SERVER_URL_FALLBACK,
      })
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
    enabled,
    fetchCollabAuthResponse,
    flushCollaborationSessionEnd,
    handleProviderConnected,
    maxReconnectAttempts,
    pendingDisconnectReasonRef,
    permissionsRef,
    recordLocalEdit,
    reconnectAttemptRef,
    scheduleReconnect,
    setSession,
    suppressNextAutoReconnectRef,
    tokenRef,
    updateCollaborators,
    userColor.color,
    userId,
    username,
  ])

  const reconnect = useCallback(async () => {
    resetReconnectMachine()

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
      return
    }

    await connect()
  }, [
    applyConnectionEvent,
    connect,
    disconnectForAccessLoss,
    fetchCollabAuthResponse,
    onErrorRef,
    resetReconnectMachine,
  ])

  const disconnect = useCallback(() => {
    clearReconnectTimeout()
    clearBackgroundIntervals()
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

    resetSessionTracking()
    resetAccessState()
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
  }, [
    clearBackgroundIntervals,
    clearReconnectTimeout,
    documentId,
    flushCollaborationSessionEnd,
    removeSession,
    resetAccessState,
    resetSessionTracking,
  ])

  useCollaborationNetworkLifecycle({
    documentId,
    enabled,
    autoReconnect,
    connectionStateRef,
    reconnectAttemptRef,
    applyConnectionEvent,
    onOfflineChange: onOfflineChangeRef.current,
    connect,
    disconnect,
  })

  const clearLocalData = useCallback(async () => {
    return new Promise<void>((resolve, reject) => {
      const request = indexedDB.deleteDatabase(`doc-${documentId}`)
      request.onsuccess = () => {
        setState((prev) => ({ ...prev, hasLocalChanges: false }))
        resolve()
      }
      request.onerror = () => reject(request.error)
    })
  }, [documentId])

  const getFragment = useCallback((name = 'default'): Y.XmlFragment | null => {
    if (!ydocRef.current) {
      return null
    }

    return ydocRef.current.getXmlFragment(name)
  }, [])

  useEffect(() => {
    if (providerRef.current) {
      providerRef.current.setAwarenessField('user', {
        userId: String(userId),
        username,
        color: userColor.color,
      })
    }
  }, [userColor.color, userId, username])

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
