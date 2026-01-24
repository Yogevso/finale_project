/**
 * SnapshotManager Component
 *
 * Manages collaboration snapshots (point-in-time saves during editing).
 * NOT to be confused with Versions (which are for releases).
 */

import { useEffect, useState, useCallback } from 'react'
import {
  Save,
  History,
  RotateCcw,
  Trash2,
  Pin,
  PinOff,
  ChevronDown,
  Clock,
  RefreshCw,
  AlertCircle,
  Check,
} from 'lucide-react'
import { api } from '@/lib/api'
import { formatDistanceToNow, format } from 'date-fns'

interface Snapshot {
  id: number
  document_id: number
  snapshot_type: string
  name: string | null
  description: string | null
  state_size: number
  created_by: number | null
  created_by_username: string | null
  session_id: string | null
  is_pinned: boolean
  expires_at: string | null
  created_at: string
}

interface SnapshotManagerProps {
  documentId: number
  sessionId?: string
  canEdit: boolean
  className?: string
  onSnapshotRestored?: () => void
}

// Format bytes to human-readable
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

// Get snapshot type label
function getSnapshotTypeLabel(type: string): string {
  switch (type) {
    case 'auto_save':
      return 'Auto-save'
    case 'manual_save':
      return 'Manual'
    case 'session_end':
      return 'Session End'
    case 'pre_publish':
      return 'Pre-publish'
    default:
      return type
  }
}

// Get snapshot type color
function getSnapshotTypeColor(type: string): string {
  switch (type) {
    case 'auto_save':
      return 'bg-gray-100 text-gray-700'
    case 'manual_save':
      return 'bg-blue-100 text-blue-700'
    case 'session_end':
      return 'bg-amber-100 text-amber-700'
    case 'pre_publish':
      return 'bg-purple-100 text-purple-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

export function SnapshotManager({
  documentId,
  sessionId,
  canEdit,
  className = '',
  onSnapshotRestored,
}: SnapshotManagerProps) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const [creating, setCreating] = useState(false)
  const [restoring, setRestoring] = useState<number | null>(null)
  const [confirmRestore, setConfirmRestore] = useState<number | null>(null)

  const fetchSnapshots = useCallback(async () => {
    try {
      setLoading(true)
      const response = await api.listSnapshots(documentId)
      setSnapshots(response.snapshots)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch snapshots:', err)
      setError('Failed to load snapshots')
    } finally {
      setLoading(false)
    }
  }, [documentId])

  useEffect(() => {
    fetchSnapshots()
  }, [fetchSnapshots])

  const handleCreateSnapshot = async () => {
    if (!canEdit) return

    try {
      setCreating(true)
      await api.createSnapshot(documentId, { session_id: sessionId })
      await fetchSnapshots()
    } catch (err) {
      console.error('Failed to create snapshot:', err)
      setError('Failed to create snapshot')
    } finally {
      setCreating(false)
    }
  }

  const handleRestoreSnapshot = async (snapshotId: number) => {
    if (!canEdit) return

    try {
      setRestoring(snapshotId)
      await api.restoreSnapshot(documentId, snapshotId, sessionId)
      setConfirmRestore(null)
      onSnapshotRestored?.()
      // Show success briefly
      setTimeout(() => setRestoring(null), 1000)
    } catch (err) {
      console.error('Failed to restore snapshot:', err)
      setError('Failed to restore snapshot')
      setRestoring(null)
    }
  }

  const handleTogglePin = async (snapshot: Snapshot) => {
    if (!canEdit) return

    try {
      await api.updateSnapshot(documentId, snapshot.id, { is_pinned: !snapshot.is_pinned })
      await fetchSnapshots()
    } catch (err) {
      console.error('Failed to update snapshot:', err)
    }
  }

  const handleDeleteSnapshot = async (snapshotId: number) => {
    if (!canEdit) return

    try {
      await api.deleteSnapshot(documentId, snapshotId)
      await fetchSnapshots()
    } catch (err) {
      console.error('Failed to delete snapshot:', err)
    }
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-gray-600" />
          <span className="font-medium text-sm text-gray-900">Snapshots</span>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {snapshots.length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleCreateSnapshot()
              }}
              disabled={creating}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
              title="Create snapshot"
            >
              {creating ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : (
                <Save className="w-3 h-3" />
              )}
              Save
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              fetchSnapshots()
            }}
            className="p-1 hover:bg-gray-200 rounded"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-gray-500" />
          </button>
          <ChevronDown
            className={`w-4 h-4 text-gray-500 transition-transform ${
              isExpanded ? '' : '-rotate-90'
            }`}
          />
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-2 bg-red-50 text-red-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Snapshot list */}
      {isExpanded && (
        <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
              <span className="text-sm">Loading snapshots...</span>
            </div>
          ) : snapshots.length === 0 ? (
            <div className="p-4 text-center text-gray-500 text-sm">
              <History className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              <p>No snapshots yet</p>
              {canEdit && (
                <p className="text-xs mt-1">Click "Save" to create your first snapshot</p>
              )}
            </div>
          ) : (
            snapshots.map((snapshot) => (
              <div key={snapshot.id} className="p-3 hover:bg-gray-50">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-gray-900 truncate">
                        {snapshot.name || 'Untitled'}
                      </span>
                      {snapshot.is_pinned && (
                        <Pin className="w-3 h-3 text-blue-500 flex-shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded ${getSnapshotTypeColor(
                          snapshot.snapshot_type
                        )}`}
                      >
                        {getSnapshotTypeLabel(snapshot.snapshot_type)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatBytes(snapshot.state_size)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      <span title={format(new Date(snapshot.created_at), 'PPpp')}>
                        {formatDistanceToNow(new Date(snapshot.created_at), { addSuffix: true })}
                      </span>
                      {snapshot.created_by_username && (
                        <span>by {snapshot.created_by_username}</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  {canEdit && (
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {confirmRestore === snapshot.id ? (
                        <div className="flex items-center gap-1 bg-amber-50 p-1 rounded">
                          <span className="text-xs text-amber-700">Restore?</span>
                          <button
                            onClick={() => handleRestoreSnapshot(snapshot.id)}
                            disabled={restoring === snapshot.id}
                            className="p-1 bg-amber-600 text-white rounded hover:bg-amber-700"
                            title="Confirm restore"
                          >
                            {restoring === snapshot.id ? (
                              <RefreshCw className="w-3 h-3 animate-spin" />
                            ) : (
                              <Check className="w-3 h-3" />
                            )}
                          </button>
                          <button
                            onClick={() => setConfirmRestore(null)}
                            className="p-1 text-gray-500 hover:bg-gray-200 rounded"
                            title="Cancel"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={() => setConfirmRestore(snapshot.id)}
                            className="p-1.5 text-gray-500 hover:bg-gray-200 rounded"
                            title="Restore to this snapshot"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleTogglePin(snapshot)}
                            className={`p-1.5 rounded ${
                              snapshot.is_pinned
                                ? 'text-blue-600 hover:bg-blue-50'
                                : 'text-gray-500 hover:bg-gray-200'
                            }`}
                            title={snapshot.is_pinned ? 'Unpin' : 'Pin (prevent auto-delete)'}
                          >
                            {snapshot.is_pinned ? (
                              <PinOff className="w-4 h-4" />
                            ) : (
                              <Pin className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => handleDeleteSnapshot(snapshot.id)}
                            className="p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600 rounded"
                            title="Delete snapshot"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// Compact button version for toolbar
export function SnapshotButton({
  documentId,
  sessionId,
  canEdit,
  className = '',
}: {
  documentId: number
  sessionId?: string
  canEdit: boolean
  className?: string
}) {
  const [creating, setCreating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  const handleCreate = async () => {
    if (!canEdit || creating) return

    try {
      setCreating(true)
      await api.createSnapshot(documentId, { session_id: sessionId })
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 2000)
    } catch (err) {
      console.error('Failed to create snapshot:', err)
    } finally {
      setCreating(false)
    }
  }

  return (
    <button
      onClick={handleCreate}
      disabled={!canEdit || creating}
      className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded transition-colors ${
        showSuccess
          ? 'bg-green-100 text-green-700'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50'
      } ${className}`}
      title="Create a snapshot (point-in-time save)"
    >
      {creating ? (
        <RefreshCw className="w-4 h-4 animate-spin" />
      ) : showSuccess ? (
        <Check className="w-4 h-4" />
      ) : (
        <Save className="w-4 h-4" />
      )}
      <span>{showSuccess ? 'Saved!' : 'Snapshot'}</span>
    </button>
  )
}

export default SnapshotManager
