import { useCallback, useEffect, useRef, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { HocuspocusProvider } from '@hocuspocus/provider'
import { getReconnectDelay } from '@/lib/collaborationReconnect'
import { reportRuntimeWarning } from '@/lib/runtimeReporter'
import {
  COLLAB_ACCESS_RECHECK_INTERVAL_MS,
  COLLAB_ACCESS_REVOKED_MESSAGE,
  COLLAB_TOKEN_REFRESH_INTERVAL_MS,
  getHttpStatusCode,
} from './collaborationRuntime'
import type { CollaborationAuthResponse, CollaborationState } from './types'
import type { CollaborationConnectionMachineEvent } from '@/features/collaboration'

interface UseCollaborationAccessOptions {
  documentId: number
  isConnected: boolean
  maxReconnectAttempts: number
  providerRef: MutableRefObject<HocuspocusProvider | null>
  connectionStateRef: MutableRefObject<{
    isConnected: boolean
    isConnecting: boolean
    isOffline: boolean
  }>
  setState: Dispatch<SetStateAction<CollaborationState>>
  applyConnectionEvent: (event: CollaborationConnectionMachineEvent) => void
  onErrorRef: MutableRefObject<((error: Error) => void) | undefined>
  onPermissionChangeRef: MutableRefObject<
    ((permissions: string[], isReadOnly: boolean) => void) | undefined
  >
  getCollabToken: (documentId: number) => Promise<CollaborationAuthResponse>
}

export function useCollaborationAccess({
  documentId,
  isConnected,
  maxReconnectAttempts,
  providerRef,
  connectionStateRef,
  setState,
  applyConnectionEvent,
  onErrorRef,
  onPermissionChangeRef,
  getCollabToken,
}: UseCollaborationAccessOptions) {
  const tokenRef = useRef<string | null>(null)
  const permissionsRef = useRef<string[]>([])
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const tokenRefreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const accessRecheckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const suppressNextAutoReconnectRef = useRef(false)
  const pendingDisconnectReasonRef = useRef<string | null>(null)

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
  }, [])

  const clearBackgroundIntervals = useCallback(() => {
    if (tokenRefreshIntervalRef.current) {
      clearInterval(tokenRefreshIntervalRef.current)
      tokenRefreshIntervalRef.current = null
    }
    if (accessRecheckIntervalRef.current) {
      clearInterval(accessRecheckIntervalRef.current)
      accessRecheckIntervalRef.current = null
    }
  }, [])

  const applyCollabAuthResponse = useCallback(
    (tokenResponse: CollaborationAuthResponse) => {
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
    },
    [onPermissionChangeRef, setState],
  )

  const fetchCollabAuthResponse = useCallback(async () => {
    const tokenResponse = await getCollabToken(documentId)
    applyCollabAuthResponse(tokenResponse)
    return tokenResponse
  }, [applyCollabAuthResponse, documentId, getCollabToken])

  const resetReconnectMachine = useCallback(() => {
    clearReconnectTimeout()
    reconnectAttemptRef.current = 0
    applyConnectionEvent({ type: 'RECONNECT_RESET' })
  }, [applyConnectionEvent, clearReconnectTimeout])

  const reconnectProviderWithFreshToken = useCallback(async () => {
    const provider = providerRef.current
    if (!provider || !connectionStateRef.current.isConnected) {
      return
    }

    resetReconnectMachine()
    suppressNextAutoReconnectRef.current = true

    try {
      provider.disconnect()
      await provider.connect()
    } catch (error) {
      suppressNextAutoReconnectRef.current = false
      throw error
    }
  }, [connectionStateRef, providerRef, resetReconnectMachine])

  const disconnectForAccessLoss = useCallback(
    (message: string = COLLAB_ACCESS_REVOKED_MESSAGE) => {
      pendingDisconnectReasonRef.current = message
      permissionsRef.current = []
      resetReconnectMachine()
      suppressNextAutoReconnectRef.current = true

      setState((prev) => ({
        ...prev,
        permissions: [],
        isReadOnly: true,
        persistenceWarning: null,
      }))

      onErrorRef.current?.(new Error(message))
      providerRef.current?.disconnect()
    },
    [onErrorRef, providerRef, resetReconnectMachine, setState],
  )

  const scheduleReconnect = useCallback(() => {
    clearReconnectTimeout()

    reconnectAttemptRef.current += 1
    const attempt = reconnectAttemptRef.current
    const delay = getReconnectDelay(attempt)

    applyConnectionEvent({
      type: 'RECONNECT_SCHEDULED',
      attempt,
      delayMs: delay,
      maxAttempts: maxReconnectAttempts,
    })

    reconnectTimeoutRef.current = setTimeout(async () => {
      if (!providerRef.current) {
        return
      }

      try {
        await fetchCollabAuthResponse()
      } catch (error) {
        const statusCode = getHttpStatusCode(error)
        if (statusCode === 401 || statusCode === 403) {
          disconnectForAccessLoss()
          return
        }
      }

      providerRef.current.connect()
    }, delay)
  }, [
    applyConnectionEvent,
    clearReconnectTimeout,
    disconnectForAccessLoss,
    fetchCollabAuthResponse,
    maxReconnectAttempts,
    providerRef,
  ])

  const refreshPermissions = useCallback(async () => {
    try {
      await fetchCollabAuthResponse()
      await reconnectProviderWithFreshToken()
    } catch (error) {
      const statusCode = getHttpStatusCode(error)
      if (statusCode === 401 || statusCode === 403) {
        disconnectForAccessLoss()
        return
      }

      reportRuntimeWarning({
        scope: 'collaboration.access',
        message: 'Failed to refresh permissions',
        error,
        userMessage: 'Live editing permissions could not be refreshed. Trying again automatically.',
        toastTitle: 'Collaboration degraded',
        dedupeKey: `collab-refresh-permissions:${documentId}`,
      })
    }
  }, [disconnectForAccessLoss, documentId, fetchCollabAuthResponse, reconnectProviderWithFreshToken])

  const resetAccessState = useCallback(() => {
    clearReconnectTimeout()
    clearBackgroundIntervals()
    tokenRef.current = null
    permissionsRef.current = []
    reconnectAttemptRef.current = 0
    suppressNextAutoReconnectRef.current = false
    pendingDisconnectReasonRef.current = null
  }, [clearBackgroundIntervals, clearReconnectTimeout])

  const canEdit = useCallback(() => {
    return permissionsRef.current.includes('write')
  }, [])

  useEffect(() => {
    if (isConnected) {
      clearBackgroundIntervals()

      tokenRefreshIntervalRef.current = setInterval(async () => {
        try {
          await fetchCollabAuthResponse()
          await reconnectProviderWithFreshToken()
        } catch (error) {
          const statusCode = getHttpStatusCode(error)
          if (statusCode === 401 || statusCode === 403) {
            disconnectForAccessLoss()
            return
          }

          reportRuntimeWarning({
            scope: 'collaboration.access',
            message: 'Collaboration token refresh failed',
            error,
            userMessage: 'Live editing credentials could not be refreshed. Trying again automatically.',
            toastTitle: 'Collaboration degraded',
            dedupeKey: `collab-token-refresh:${documentId}`,
          })
        }
      }, COLLAB_TOKEN_REFRESH_INTERVAL_MS)

      return () => {
        clearBackgroundIntervals()
      }
    }

    clearBackgroundIntervals()
    return undefined
  }, [
    clearBackgroundIntervals,
    disconnectForAccessLoss,
    fetchCollabAuthResponse,
    isConnected,
    reconnectProviderWithFreshToken,
  ])

  useEffect(() => {
    if (isConnected) {
      if (accessRecheckIntervalRef.current) {
        clearInterval(accessRecheckIntervalRef.current)
      }

      accessRecheckIntervalRef.current = setInterval(async () => {
        try {
          await fetchCollabAuthResponse()
        } catch (error) {
          const statusCode = getHttpStatusCode(error)
          if (statusCode === 401 || statusCode === 403) {
            disconnectForAccessLoss()
            return
          }

          reportRuntimeWarning({
            scope: 'collaboration.access',
            message: 'Collaboration access re-check failed',
            error,
            userMessage: 'Live editing access could not be re-verified. Trying again automatically.',
            toastTitle: 'Collaboration degraded',
            dedupeKey: `collab-access-recheck:${documentId}`,
          })
        }
      }, COLLAB_ACCESS_RECHECK_INTERVAL_MS)

      return () => {
        if (accessRecheckIntervalRef.current) {
          clearInterval(accessRecheckIntervalRef.current)
          accessRecheckIntervalRef.current = null
        }
      }
    }

    if (accessRecheckIntervalRef.current) {
      clearInterval(accessRecheckIntervalRef.current)
      accessRecheckIntervalRef.current = null
    }

    return undefined
  }, [disconnectForAccessLoss, fetchCollabAuthResponse, isConnected])

  useEffect(() => {
    return () => {
      clearReconnectTimeout()
      clearBackgroundIntervals()
    }
  }, [clearBackgroundIntervals, clearReconnectTimeout])

  return {
    tokenRef,
    permissionsRef,
    reconnectTimeoutRef,
    reconnectAttemptRef,
    suppressNextAutoReconnectRef,
    pendingDisconnectReasonRef,
    fetchCollabAuthResponse,
    reconnectProviderWithFreshToken,
    disconnectForAccessLoss,
    scheduleReconnect,
    clearReconnectTimeout,
    resetReconnectMachine,
    resetAccessState,
    clearBackgroundIntervals,
    refreshPermissions,
    canEdit,
  }
}
