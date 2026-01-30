/**
 * CollaborationStatus Component
 *
 * Displays the connection status and active collaborators
 * for real-time document editing.
 */

import { CollaboratorInfo } from '@/lib/useCollaboration'

interface CollaborationStatusProps {
  isConnected: boolean
  isConnecting: boolean
  isSynced: boolean
  error: string | null
  collaborators: CollaboratorInfo[]
  onRetry?: () => void
}

export function CollaborationStatus({
  isConnected,
  isConnecting,
  isSynced,
  error,
  collaborators,
  onRetry,
}: CollaborationStatusProps) {
  // Filter out duplicates and current user (show only others)
  const otherCollaborators = collaborators.filter(
    (c, index, self) => self.findIndex((o) => o.userId === c.userId) === index
  )

  return (
    <div className="flex items-center gap-3">
      {/* Connection Status Indicator */}
      <div className="flex items-center gap-2">
        {isConnecting && (
          <div className="flex items-center gap-1.5 text-amber-600">
            <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-xs">Connecting...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-1.5 text-rose-600">
            <div className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="text-xs">Disconnected</span>
            {onRetry && (
              <button
                onClick={onRetry}
                className="text-xs text-sky-600 hover:text-sky-700 underline ml-1"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {isConnected && !isSynced && (
          <div className="flex items-center gap-1.5 text-sky-600">
            <div className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
            <span className="text-xs">Syncing...</span>
          </div>
        )}

        {isConnected && isSynced && (
          <div className="flex items-center gap-1.5 text-emerald-600">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs">Live</span>
          </div>
        )}
      </div>

      {/* Collaborators Avatars */}
      {otherCollaborators.length > 0 && (
        <div className="flex items-center">
          <div className="flex -space-x-2">
            {otherCollaborators.slice(0, 5).map((collaborator) => (
              <div
                key={collaborator.clientId}
                className="relative group"
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-medium border-2 border-white shadow-sm"
                  style={{ backgroundColor: collaborator.color }}
                  title={collaborator.username}
                >
                  {collaborator.username.charAt(0).toUpperCase()}
                </div>
                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-900 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  {collaborator.username}
                </div>
              </div>
            ))}
          </div>

          {otherCollaborators.length > 5 && (
            <div className="ml-1 px-2 py-0.5 bg-slate-100 rounded-full text-xs text-slate-600">
              +{otherCollaborators.length - 5}
            </div>
          )}

          <span className="ml-2 text-xs text-slate-500">
            {otherCollaborators.length} editing
          </span>
        </div>
      )}
    </div>
  )
}

/**
 * Compact version for toolbar integration
 */
export function CollaborationStatusCompact({
  isConnected,
  isConnecting,
  collaborators,
}: Pick<CollaborationStatusProps, 'isConnected' | 'isConnecting' | 'collaborators'>) {
  const count = collaborators.length

  if (isConnecting) {
    return (
      <div className="flex items-center gap-1 text-amber-600">
        <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
      </div>
    )
  }

  if (!isConnected) {
    return (
      <div className="flex items-center gap-1 text-slate-400">
        <div className="w-2 h-2 rounded-full bg-slate-400" />
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2 h-2 rounded-full bg-emerald-500" />
      {count > 1 && (
        <span className="text-xs text-slate-500">{count}</span>
      )}
    </div>
  )
}

export default CollaborationStatus
