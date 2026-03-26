import { HocuspocusProvider } from '@hocuspocus/provider'
import { IndexeddbPersistence } from 'y-indexeddb'
import * as Y from 'yjs'
import { getUserColor } from '@/lib/userColors'
import { parseCollabServerStatelessMessage, resolveCollabServerUrl } from './collaborationRuntime'
import type { CollaborationAuthResponse, CollaborationState } from './types'
import type { CollaborationConnectionMachineEvent } from '@/features/collaboration'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'

interface CollaborationStoreSessionPatch {
  documentTitle?: string
  isConnected?: boolean
  isSynced?: boolean
}

interface EstablishCollaborationConnectionOptions {
  documentId: number
  username: string
  userId: string | number
  userColor: string
  fallbackCollabServerUrl: string
  autoReconnect: boolean
  maxReconnectAttempts: number
  fetchCollabAuthResponse: () => Promise<CollaborationAuthResponse>
  tokenRef: MutableRefObject<string | null>
  permissionsRef: MutableRefObject<string[]>
  providerRef: MutableRefObject<HocuspocusProvider | null>
  ydocRef: MutableRefObject<Y.Doc | null>
  indexeddbRef: MutableRefObject<IndexeddbPersistence | null>
  reconnectAttemptRef: MutableRefObject<number>
  suppressNextAutoReconnectRef: MutableRefObject<boolean>
  pendingDisconnectReasonRef: MutableRefObject<string | null>
  connectionStateRef: MutableRefObject<{
    isConnected: boolean
    isConnecting: boolean
    isOffline: boolean
  }>
  setState: Dispatch<SetStateAction<CollaborationState>>
  applyConnectionEvent: (event: CollaborationConnectionMachineEvent) => void
  scheduleReconnect: () => void
  setSession: (documentId: number, patch: CollaborationStoreSessionPatch) => void
  updateCollaborators: (
    documentId: number,
    collaborators: CollaborationState['collaborators'],
  ) => void
  handleProviderConnected: () => void
  flushCollaborationSessionEnd: () => Promise<void>
  recordLocalEdit: () => void
  onConnect?: () => void
  onDisconnect?: () => void
  onSynced?: () => void
  onError?: (error: Error) => void
}

export async function establishCollaborationConnection({
  documentId,
  username,
  userId,
  userColor,
  fallbackCollabServerUrl,
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
  onConnect,
  onDisconnect,
  onSynced,
  onError,
}: EstablishCollaborationConnectionOptions) {
  const tokenResponse = await fetchCollabAuthResponse()

  const ydoc = new Y.Doc()
  ydocRef.current = ydoc

  const indexeddbProvider = new IndexeddbPersistence(`doc-${documentId}`, ydoc)
  indexeddbRef.current = indexeddbProvider

  indexeddbProvider.on('synced', () => {
    setState((prev) => ({ ...prev, hasLocalChanges: false }))
  })

  ydoc.on('update', (_update: Uint8Array, origin: unknown) => {
    if (origin !== providerRef.current && permissionsRef.current.includes('write')) {
      setState((prev) => ({ ...prev, hasLocalChanges: true }))
      recordLocalEdit()
    }
  })

  const provider = new HocuspocusProvider({
    url: resolveCollabServerUrl(tokenResponse.websocket_url, fallbackCollabServerUrl),
    name: `document/${documentId}`,
    document: ydoc,
    token: () => tokenRef.current ?? '',
    onConnect: () => {
      reconnectAttemptRef.current = 0
      applyConnectionEvent({ type: 'CONNECT_SUCCEEDED' })
      handleProviderConnected()
      onConnect?.()
    },
    onDisconnect: () => {
      const suppressAutoReconnect = suppressNextAutoReconnectRef.current
      suppressNextAutoReconnectRef.current = false
      const disconnectReason = pendingDisconnectReasonRef.current
      pendingDisconnectReasonRef.current = null

      applyConnectionEvent({ type: 'DISCONNECTED' })
      void flushCollaborationSessionEnd()

      if (
        autoReconnect &&
        !connectionStateRef.current.isOffline &&
        reconnectAttemptRef.current < maxReconnectAttempts &&
        !suppressAutoReconnect
      ) {
        scheduleReconnect()
      }

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

      onDisconnect?.()
    },
    onSynced: () => {
      applyConnectionEvent({ type: 'SYNCED' })
      setSession(documentId, { isSynced: true })
      onSynced?.()
    },
    onAwarenessUpdate: ({ states }) => {
      const collaborators = Array.from(states.entries())
        .filter(([, awarenessState]) => Boolean(awarenessState.user))
        .map(([clientId, awarenessState]) => ({
          clientId,
          userId: awarenessState.user.userId || awarenessState.user.id,
          username: awarenessState.user.username || awarenessState.user.name,
          color:
            awarenessState.user.color ||
            getUserColor(awarenessState.user.userId || clientId).color,
          cursor: awarenessState.cursor,
        }))

      setState((prev) => ({ ...prev, collaborators }))
      updateCollaborators(documentId, collaborators)
    },
    onAuthenticationFailed: ({ reason }) => {
      const error = new Error(`Authentication failed: ${reason}`)
      applyConnectionEvent({
        type: 'CONNECT_FAILED',
        error: error.message,
      })
      onError?.(error)
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
        onError?.(new Error(message.message))
        return
      }

      setState((prev) => ({
        ...prev,
        persistenceWarning: null,
      }))
    },
  })

  providerRef.current = provider
  provider.setAwarenessField('user', {
    userId: String(userId),
    username,
    color: userColor,
  })

  setState((prev) => ({
    ...prev,
    provider,
    ydoc,
  }))
}
