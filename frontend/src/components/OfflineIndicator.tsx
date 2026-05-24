/**
 * OfflineIndicator Component
 *
 * Displays offline status, connection issues, and provides
 * reconnection controls and local data management.
 */

import { useId, useState } from 'react'
import {
  WifiOff,
  RefreshCw,
  AlertTriangle,
  Cloud,
  CloudOff,
  HardDrive,
  Trash2,
  Check,
  X,
} from 'lucide-react'

interface OfflineIndicatorProps {
  isConnected: boolean
  isConnecting: boolean
  isSynced: boolean
  isOffline: boolean
  hasLocalChanges: boolean
  reconnectAttempt: number
  error: string | null
  onReconnect: () => void
  onClearLocalData?: () => Promise<void>
  className?: string
}

type StatusConfig = {
  icon: typeof WifiOff
  label: string
  description: string
  color: string
  bgColor: string
  borderColor: string
  animate?: boolean
}

export function OfflineIndicator({
  isConnected,
  isConnecting,
  isSynced,
  isOffline,
  hasLocalChanges,
  reconnectAttempt,
  error,
  onReconnect,
  onClearLocalData,
  className = '',
}: OfflineIndicatorProps) {
  const detailsId = useId()
  const [isClearing, setIsClearing] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  const getStatus = (): StatusConfig => {
    if (isOffline) {
      return {
        icon: WifiOff,
        label: 'Offline',
        description: 'No internet connection. Changes are saved locally.',
        color: 'text-slate-600 dark:text-slate-300',
        bgColor: 'bg-slate-100 dark:bg-slate-800',
        borderColor: 'border-slate-300 dark:border-slate-700',
      }
    }

    if (isConnecting) {
      return {
        icon: RefreshCw,
        label: 'Connecting',
        description:
          reconnectAttempt > 0
            ? `Reconnecting... (attempt ${reconnectAttempt})`
            : 'Establishing connection...',
        color: 'text-blue-600 dark:text-blue-300',
        bgColor: 'bg-blue-50 dark:bg-blue-950/30',
        borderColor: 'border-blue-200 dark:border-blue-900/70',
        animate: true,
      }
    }

    if (error && !isConnected) {
      return {
        icon: AlertTriangle,
        label: 'Disconnected',
        description: error,
        color: 'text-rose-600 dark:text-rose-300',
        bgColor: 'bg-rose-50 dark:bg-rose-950/30',
        borderColor: 'border-rose-200 dark:border-rose-900/70',
      }
    }

    if (isConnected && !isSynced) {
      return {
        icon: Cloud,
        label: 'Syncing',
        description: 'Synchronizing with server...',
        color: 'text-blue-600 dark:text-blue-300',
        bgColor: 'bg-blue-50 dark:bg-blue-950/30',
        borderColor: 'border-blue-200 dark:border-blue-900/70',
        animate: true,
      }
    }

    if (isConnected && isSynced) {
      return {
        icon: Check,
        label: 'Connected',
        description: hasLocalChanges ? 'All changes synced' : 'Up to date',
        color: 'text-emerald-600 dark:text-emerald-300',
        bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
        borderColor: 'border-emerald-200 dark:border-emerald-900/70',
      }
    }

    return {
      icon: CloudOff,
      label: 'Disconnected',
      description: 'Waiting for collaboration server...',
      color: 'text-slate-600 dark:text-slate-300',
      bgColor: 'bg-slate-100 dark:bg-slate-800',
      borderColor: 'border-slate-300 dark:border-slate-700',
    }
  }

  const status = getStatus()
  const StatusIcon = status.icon

  const handleClearLocalData = async () => {
    if (!onClearLocalData || isClearing) {
      return
    }

    setIsClearing(true)
    try {
      await onClearLocalData()
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <div className={`relative ${className}`} role="status" aria-live="polite">
      <button
        type="button"
        onClick={() => setShowDetails((current) => !current)}
        className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 transition-colors hover:opacity-80 ${status.bgColor} ${status.borderColor}`}
        aria-expanded={showDetails}
        aria-controls={detailsId}
        aria-haspopup="dialog"
        aria-label={`Connection status: ${status.label}`}
      >
        <StatusIcon className={`h-4 w-4 ${status.color} ${status.animate ? 'sync-status-pulse' : ''}`} />
        <span className={`text-sm font-medium ${status.color}`}>{status.label}</span>
        {hasLocalChanges && !isSynced && (
          <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-300">
            <HardDrive className="h-3 w-3" />
            Local changes
          </span>
        )}
      </button>

      {showDetails && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40"
            onClick={() => setShowDetails(false)}
            aria-label="Close connection status details"
          />

          <div
            id={detailsId}
            className="dropdown-menu absolute right-0 top-full z-50 mt-2 w-72 dark:bg-slate-900"
            role="dialog"
            aria-label="Connection status details"
          >
            <div className="space-y-4 p-4">
              <div className="flex items-start gap-3">
                <div className={`rounded-lg p-2 ${status.bgColor}`}>
                  <StatusIcon className={`h-5 w-5 ${status.color} ${status.animate ? 'sync-status-pulse' : ''}`} />
                </div>
                <div className="flex-1">
                  <h4 className={`font-semibold ${status.color}`}>{status.label}</h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{status.description}</p>
                </div>
              </div>

              <div className="space-y-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Internet</span>
                  <span className={isOffline ? 'text-rose-600 dark:text-rose-300' : 'text-emerald-600 dark:text-emerald-300'}>
                    {isOffline ? 'Offline' : 'Online'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Server</span>
                  <span className={isConnected ? 'text-emerald-600 dark:text-emerald-300' : 'text-slate-500 dark:text-slate-400'}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Synced</span>
                  <span className={isSynced ? 'text-emerald-600 dark:text-emerald-300' : 'text-amber-600 dark:text-amber-300'}>
                    {isSynced ? 'Yes' : 'Pending'}
                  </span>
                </div>
                {hasLocalChanges && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500 dark:text-slate-400">Local changes</span>
                    <span className="text-amber-600 dark:text-amber-300">Unsaved</span>
                  </div>
                )}
              </div>

              <div className="space-y-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                {(!isConnected || error) && !isConnecting && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowDetails(false)
                      onReconnect()
                    }}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-2 text-white transition-colors hover:bg-blue-700"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Reconnect Now
                  </button>
                )}

                {onClearLocalData && (
                  <button
                    type="button"
                    onClick={handleClearLocalData}
                    disabled={isClearing}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-rose-200 px-3 py-2 text-rose-600 transition-colors hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900/70 dark:text-rose-300 dark:hover:bg-rose-950/20"
                  >
                    <Trash2 className="h-4 w-4" />
                    {isClearing ? 'Clearing...' : 'Clear Local Data'}
                  </button>
                )}
              </div>

              <p className="text-center text-xs text-slate-400 dark:text-slate-500">
                Your edits are automatically saved locally when offline
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export function OfflineIndicatorCompact({
  isConnected,
  isOffline,
  isSynced,
  hasLocalChanges,
  className = '',
}: Pick<OfflineIndicatorProps, 'isConnected' | 'isOffline' | 'isSynced' | 'hasLocalChanges' | 'className'>) {
  if (isConnected && isSynced && !hasLocalChanges) {
    return null
  }

  if (isOffline) {
    return (
      <div
        className={`flex items-center gap-1 rounded-full bg-slate-200 px-2 py-1 text-xs text-slate-700 ${className}`}
        title="Working offline - changes saved locally"
        role="status"
        aria-live="polite"
      >
        <WifiOff className="h-3 w-3" />
        <span>Offline</span>
      </div>
    )
  }

  if (!isConnected) {
    return (
      <div
        className={`flex items-center gap-1 rounded-full bg-rose-100 px-2 py-1 text-xs text-rose-700 ${className}`}
        title="Disconnected from server"
        role="status"
        aria-live="polite"
      >
        <CloudOff className="h-3 w-3" />
        <span>Disconnected</span>
      </div>
    )
  }

  if (hasLocalChanges || !isSynced) {
    return (
      <div
        className={`flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-700 ${className}`}
        title="Syncing changes..."
        role="status"
        aria-live="polite"
      >
        <Cloud className="sync-status-pulse h-3 w-3" />
        <span>Syncing</span>
      </div>
    )
  }

  return null
}

export function OfflineBanner({
  isOffline,
  isConnected,
  hasLocalChanges,
  reconnectAttempt,
  error,
  onReconnect,
  onDismiss,
}: Pick<OfflineIndicatorProps, 'isOffline' | 'isConnected' | 'hasLocalChanges' | 'reconnectAttempt' | 'error' | 'onReconnect'> & {
  onDismiss?: () => void
}) {
  if (!isOffline && isConnected && !error) {
    return null
  }

  if (isOffline) {
    return (
      <div
        className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-100 px-4 py-2"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center gap-2">
          <WifiOff className="h-4 w-4 text-slate-600" />
          <span className="text-sm text-slate-700">
            You're offline. Don't worry, your changes are being saved locally.
          </span>
        </div>
        {hasLocalChanges && (
          <span className="flex items-center gap-1 text-xs text-amber-600">
            <HardDrive className="h-3 w-3" />
            Local changes pending sync
          </span>
        )}
      </div>
    )
  }

  if (!isConnected && error) {
    return (
      <div
        className="flex items-center justify-between gap-3 border-b border-rose-200 bg-rose-50 px-4 py-2"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-rose-600" />
          <span className="text-sm text-rose-700">
            {reconnectAttempt > 0
              ? `Connection lost. Reconnecting... (attempt ${reconnectAttempt})`
              : 'Connection to the collaboration server was lost.'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onReconnect}
            className="rounded bg-rose-600 px-3 py-1 text-sm text-white transition-colors hover:bg-rose-700"
          >
            Reconnect
          </button>
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="text-rose-400 transition-colors hover:text-rose-600"
              aria-label="Dismiss connection error banner"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    )
  }

  return null
}

export default OfflineIndicator
