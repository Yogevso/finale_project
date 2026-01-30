/**
 * PresenceIndicator Component
 *
 * Shows real-time presence of collaborators with avatars,
 * user count, and optional detailed popover.
 */

import { useMemo, useState } from 'react'
import { Users, Circle, Eye, Edit3 } from 'lucide-react'
import { CollaboratorInfo } from '@/lib/useCollaboration'

interface PresenceIndicatorProps {
  collaborators: CollaboratorInfo[]
  currentUserId: string | number
  maxAvatars?: number
  showCount?: boolean
  showPopover?: boolean
  className?: string
}

interface CollaboratorAvatarProps {
  collaborator: CollaboratorInfo
  isCurrentUser: boolean
  size?: 'sm' | 'md' | 'lg'
}

function CollaboratorAvatar({
  collaborator,
  isCurrentUser,
  size = 'md',
}: CollaboratorAvatarProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
  }

  const initial = collaborator.username?.charAt(0)?.toUpperCase() || '?'

  return (
    <div
      className="relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div
        className={`relative rounded-full flex items-center justify-center font-medium text-white ring-2 ring-white transition-transform hover:scale-110 cursor-pointer ${sizeClasses[size]} ${isCurrentUser ? 'ring-sky-500' : ''}`}
        style={{ backgroundColor: collaborator.color }}
      >
        {initial}

        {/* Online indicator */}
        <Circle
          className="absolute -bottom-0.5 -right-0.5 w-3 h-3 fill-emerald-500 text-emerald-500"
        />
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-900 text-white text-xs rounded whitespace-nowrap z-50 pointer-events-none">
          <div className="text-center">
            <p className="font-medium">
              {collaborator.username}
              {isCurrentUser && ' (you)'}
            </p>
            {collaborator.cursor && (
              <p className="text-xs text-slate-300 flex items-center gap-1 justify-center">
                <Edit3 className="w-3 h-3" />
                Currently editing
              </p>
            )}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
        </div>
      )}
    </div>
  )
}

export function PresenceIndicator({
  collaborators,
  currentUserId,
  maxAvatars = 5,
  showCount = true,
  showPopover = true,
  className = '',
}: PresenceIndicatorProps) {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)

  // Sort collaborators: current user first, then by username
  const sortedCollaborators = useMemo(() => {
    return [...collaborators].sort((a, b) => {
      const aIsCurrent = String(a.userId) === String(currentUserId)
      const bIsCurrent = String(b.userId) === String(currentUserId)

      if (aIsCurrent && !bIsCurrent) return -1
      if (!aIsCurrent && bIsCurrent) return 1

      return a.username.localeCompare(b.username)
    })
  }, [collaborators, currentUserId])

  // Split into visible and overflow
  const visibleCollaborators = sortedCollaborators.slice(0, maxAvatars)
  const overflowCount = Math.max(0, sortedCollaborators.length - maxAvatars)

  if (collaborators.length === 0) {
    return (
      <div className={`flex items-center gap-2 text-slate-500 ${className}`}>
        <Users className="w-4 h-4" />
        <span className="text-sm">No collaborators</span>
      </div>
    )
  }

  const avatarStack = (
    <div className="flex items-center">
      {/* Avatar stack */}
      <div className="flex -space-x-2">
        {visibleCollaborators.map((collaborator) => (
          <CollaboratorAvatar
            key={collaborator.clientId}
            collaborator={collaborator}
            isCurrentUser={String(collaborator.userId) === String(currentUserId)}
            size="md"
          />
        ))}

        {/* Overflow indicator */}
        {overflowCount > 0 && (
          <div
            className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium ring-2 ring-white cursor-pointer"
            title={`${overflowCount} more collaborator${overflowCount > 1 ? 's' : ''}`}
          >
            +{overflowCount}
          </div>
        )}
      </div>

      {/* Count badge */}
      {showCount && (
        <span className="ml-2 px-2 py-0.5 bg-slate-100 rounded-full text-xs font-medium text-slate-600 flex items-center gap-1">
          <Users className="w-3 h-3" />
          {collaborators.length}
        </span>
      )}
    </div>
  )

  if (!showPopover) {
    return <div className={className}>{avatarStack}</div>
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsPopoverOpen(!isPopoverOpen)}
        className="p-1 hover:bg-slate-100 rounded-xl transition-colors"
      >
        {avatarStack}
      </button>

      {/* Popover */}
      {isPopoverOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsPopoverOpen(false)}
          />

          {/* Popover content */}
          <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold">Collaborators</h4>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-xs">
                  {collaborators.length} online
                </span>
              </div>

              <div className="max-h-64 overflow-y-auto space-y-2">
                {sortedCollaborators.map((collaborator) => {
                  const isCurrentUser = String(collaborator.userId) === String(currentUserId)
                  const isEditing = !!collaborator.cursor

                  return (
                    <div
                      key={collaborator.clientId}
                      className="flex items-center gap-3 p-2 rounded-xl hover:bg-slate-50 transition-colors"
                    >
                      <CollaboratorAvatar
                        collaborator={collaborator}
                        isCurrentUser={isCurrentUser}
                        size="md"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">
                          {collaborator.username}
                          {isCurrentUser && (
                            <span className="text-slate-500 ml-1">(you)</span>
                          )}
                        </p>
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                          {isEditing ? (
                            <>
                              <Edit3 className="w-3 h-3" />
                              Editing
                            </>
                          ) : (
                            <>
                              <Eye className="w-3 h-3" />
                              Viewing
                            </>
                          )}
                        </p>
                      </div>
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: collaborator.color }}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// Compact version for toolbars
export function PresenceIndicatorCompact({
  collaborators,
  currentUserId,
  className = '',
}: Pick<PresenceIndicatorProps, 'collaborators' | 'currentUserId' | 'className'>) {
  const otherCount = collaborators.filter(
    (c) => String(c.userId) !== String(currentUserId)
  ).length

  if (otherCount === 0) {
    return null
  }

  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 text-sm ${className}`}
      title={`${otherCount} other user${otherCount > 1 ? 's' : ''} editing this document`}
    >
      <Circle className="w-2 h-2 fill-current" />
      <span>{otherCount} editing</span>
    </div>
  )
}

export default PresenceIndicator
