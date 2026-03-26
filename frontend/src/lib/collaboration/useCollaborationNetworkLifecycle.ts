import { useEffect, type MutableRefObject } from 'react'
import type { CollaborationConnectionMachineEvent } from '@/features/collaboration'

interface UseCollaborationNetworkLifecycleOptions {
  documentId: number
  enabled: boolean
  autoReconnect: boolean
  connectionStateRef: MutableRefObject<{
    isConnected: boolean
    isConnecting: boolean
    isOffline: boolean
  }>
  reconnectAttemptRef: MutableRefObject<number>
  applyConnectionEvent: (event: CollaborationConnectionMachineEvent) => void
  onOfflineChange?: (isOffline: boolean) => void
  connect: () => Promise<void>
  disconnect: () => void
}

export function useCollaborationNetworkLifecycle({
  documentId,
  enabled,
  autoReconnect,
  connectionStateRef,
  reconnectAttemptRef,
  applyConnectionEvent,
  onOfflineChange,
  connect,
  disconnect,
}: UseCollaborationNetworkLifecycleOptions) {
  useEffect(() => {
    const handleOnline = () => {
      applyConnectionEvent({ type: 'ONLINE' })
      onOfflineChange?.(false)

      if (
        autoReconnect &&
        !connectionStateRef.current.isConnected &&
        !connectionStateRef.current.isConnecting
      ) {
        reconnectAttemptRef.current = 0
        void connect()
      }
    }

    const handleOffline = () => {
      applyConnectionEvent({ type: 'OFFLINE' })
      onOfflineChange?.(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [
    applyConnectionEvent,
    autoReconnect,
    connect,
    connectionStateRef,
    onOfflineChange,
    reconnectAttemptRef,
  ])

  useEffect(() => {
    if (
      enabled &&
      !connectionStateRef.current.isConnected &&
      !connectionStateRef.current.isConnecting
    ) {
      void connect()
    }

    return () => {
      disconnect()
    }
  }, [connect, connectionStateRef, disconnect, documentId, enabled])
}
