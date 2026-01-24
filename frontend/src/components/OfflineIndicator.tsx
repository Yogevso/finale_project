/**
 * OfflineIndicator Component
 *
 * Displays offline status, connection issues, and provides
 * reconnection controls and local data management.
 */

import { useState } from 'react'
import {
  WifiOff,
  RefreshCw,
  AlertTriangle,
  Cloud,
  CloudOff,
  HardDrive,
  Trash2,
  Check,
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
  const [isClearing, setIsClearing] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  // Determine the current status
  const getStatus = () => {
    if (isOffline) {
      return {
        icon: WifiOff,
        label: 'Offline',
        description: 'No internet connection. Changes are saved locally.',
        color: 'text-gray-600',
        bgColor: 'bg-gray-100',
        borderColor: 'border-gray-300',
      }
    }

    if (isConnecting) {
      return {
        icon: RefreshCw,
        label: 'Connecting',
        description: reconnectAttempt > 0
          ? `Reconnecting... (attempt ${reconnectAttempt})`
          : 'Establishing connection...',
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        animate: true,
      }
    }

    if (error && !isConnected) {
      return {
        icon: AlertTriangle,
        label: 'Disconnected',
        description: error,
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
      }
    }

    if (isConnected && !isSynced) {
      return {
        icon: Cloud,
        label: 'Syncing',
        description: 'Synchronizing with server...',
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        animate: true,
      }
    }

    if (isConnected && isSynced) {
      return {
        icon: Check,
        label: 'Connected',
        description: hasLocalChanges ? 'All changes synced' : 'Up to date',
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
      }
    }

    return {
      icon: CloudOff,
      label: 'Disconnected',
      description: 'Not connected to collaboration server',
      color: 'text-gray-600',
      bgColor: 'bg-gray-100',
      borderColor: 'border-gray-300',
    }
  }

  const status = getStatus()
  const StatusIcon = status.icon

  const handleClearLocalData = async () => {
    if (!onClearLocalData || isClearing) return

    setIsClearing(true)
    try {
      await onClearLocalData()
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <div className={`relative ${className}`}>
      {/* Main indicator button */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${status.bgColor} ${status.borderColor} hover:opacity-80`}
      >
        <StatusIcon
          className={`w-4 h-4 ${status.color} ${status.animate ? 'animate-spin' : ''}`}
        />
        <span className={`text-sm font-medium ${status.color}`}>
          {status.label}
        </span>
        {hasLocalChanges && !isSynced && (
          <span className="flex items-center gap-1 text-xs text-amber-600">
            <HardDrive className="w-3 h-3" />
            Local changes
          </span>
        )}
      </button>

      {/* Details dropdown */}
      {showDetails && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowDetails(false)}
          />

          {/* Dropdown content */}
          <div className="absolute right-0 top-full mt-2 w-72 bg-white rounded-lg shadow-lg border z-50">
            <div className="p-4 space-y-4">
              {/* Status section */}
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${status.bgColor}`}>
                  <StatusIcon
                    className={`w-5 h-5 ${status.color} ${status.animate ? 'animate-spin' : ''}`}
                  />
                </div>
                <div className="flex-1">
                  <h4 className={`font-semibold ${status.color}`}>
                    {status.label}
                  </h4>
                  <p className="text-sm text-gray-600">{status.description}</p>
                </div>
              </div>

              {/* Connection info */}
              <div className="border-t pt-3 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Internet</span>
                  <span className={isOffline ? 'text-red-600' : 'text-green-600'}>
                    {isOffline ? 'Offline' : 'Online'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Server</span>
                  <span className={isConnected ? 'text-green-600' : 'text-gray-500'}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Synced</span>
                  <span className={isSynced ? 'text-green-600' : 'text-amber-600'}>
                    {isSynced ? 'Yes' : 'Pending'}
                  </span>
                </div>
                {hasLocalChanges && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Local changes</span>
                    <span className="text-amber-600">Unsaved</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="border-t pt-3 space-y-2">
                {(!isConnected || error) && !isConnecting && (
                  <button
                    onClick={() => {
                      setShowDetails(false)
                      onReconnect()
                    }}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reconnect Now
                  </button>
                )}

                {onClearLocalData && (
                  <button
                    onClick={handleClearLocalData}
                    disabled={isClearing}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                    {isClearing ? 'Clearing...' : 'Clear Local Data'}
                  </button>
                )}
              </div>

              {/* Help text */}
              <p className="text-xs text-gray-400 text-center">
                Your edits are automatically saved locally when offline
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// Compact version - just shows an icon
export function OfflineIndicatorCompact({
  isConnected,
  isOffline,
  isSynced,
  hasLocalChanges,
  className = '',
}: Pick<OfflineIndicatorProps, 'isConnected' | 'isOffline' | 'isSynced' | 'hasLocalChanges' | 'className'>) {
  if (isConnected && isSynced && !hasLocalChanges) {
    // Don't show anything when fully synced
    return null
  }

  if (isOffline) {
    return (
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded-full bg-gray-200 text-gray-700 text-xs ${className}`}
        title="Working offline - changes saved locally"
      >
        <WifiOff className="w-3 h-3" />
        <span>Offline</span>
      </div>
    )
  }

  if (!isConnected) {
    return (
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded-full bg-red-100 text-red-700 text-xs ${className}`}
        title="Disconnected from server"
      >
        <CloudOff className="w-3 h-3" />
        <span>Disconnected</span>
      </div>
    )
  }

  if (hasLocalChanges || !isSynced) {
    return (
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded-full bg-amber-100 text-amber-700 text-xs ${className}`}
        title="Syncing changes..."
      >
        <Cloud className="w-3 h-3 animate-pulse" />
        <span>Syncing</span>
      </div>
    )
  }

  return null
}

// Banner version for showing at the top of the editor
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
  // Only show banner for important states
  if (!isOffline && isConnected && !error) {
    return null
  }

  if (isOffline) {
    return (
      <div className="flex items-center justify-between gap-3 px-4 py-2 bg-gray-100 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <WifiOff className="w-4 h-4 text-gray-600" />
          <span className="text-sm text-gray-700">
            You're offline. Don't worry, your changes are being saved locally.
          </span>
        </div>
        {hasLocalChanges && (
          <span className="text-xs text-amber-600 flex items-center gap-1">
            <HardDrive className="w-3 h-3" />
            Local changes pending sync
          </span>
        )}
      </div>
    )
  }

  if (!isConnected && error) {
    return (
      <div className="flex items-center justify-between gap-3 px-4 py-2 bg-red-50 border-b border-red-200">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          <span className="text-sm text-red-700">
            {reconnectAttempt > 0
              ? `Connection lost. Reconnecting... (attempt ${reconnectAttempt})`
              : 'Connection to the collaboration server was lost.'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReconnect}
            className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Reconnect
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-red-400 hover:text-red-600"
            >
              ×
            </button>
          )}
        </div>
      </div>
    )
  }

  return null
}

export default OfflineIndicator
