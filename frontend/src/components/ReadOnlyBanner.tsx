/**
 * ReadOnlyBanner Component
 *
 * Displays a banner when the user is in read-only mode
 * during collaborative editing.
 */

import { Eye, Lock, RefreshCw } from 'lucide-react'

interface ReadOnlyBannerProps {
  isReadOnly: boolean
  username?: string
  onRequestAccess?: () => void
  onRefreshPermissions?: () => void
  className?: string
}

export function ReadOnlyBanner({
  isReadOnly,
  onRequestAccess,
  onRefreshPermissions,
  className = '',
}: ReadOnlyBannerProps) {
  if (!isReadOnly) {
    return null
  }

  return (
    <div
      className={`flex items-center justify-between gap-3 px-4 py-2 bg-amber-50 border-b border-amber-200 ${className}`}
    >
      <div className="flex items-center gap-2">
        <Eye className="w-4 h-4 text-amber-600" />
        <span className="text-sm text-amber-800">
          <strong>View Only</strong> — You can view this document but cannot make changes.
        </span>
      </div>
      <div className="flex items-center gap-2">
        {onRefreshPermissions && (
          <button
            onClick={onRefreshPermissions}
            className="flex items-center gap-1 px-2 py-1 text-xs text-amber-700 hover:bg-amber-100 rounded transition-colors"
            title="Check if permissions have changed"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        )}
        {onRequestAccess && (
          <button
            onClick={onRequestAccess}
            className="flex items-center gap-1 px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors"
          >
            <Lock className="w-3 h-3" />
            Request Edit Access
          </button>
        )}
      </div>
    </div>
  )
}

// Compact badge version for toolbars
export function ReadOnlyBadge({
  isReadOnly,
  className = '',
}: Pick<ReadOnlyBannerProps, 'isReadOnly' | 'className'>) {
  if (!isReadOnly) {
    return null
  }

  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-full bg-amber-100 text-amber-700 text-xs ${className}`}
      title="You have view-only access to this document"
    >
      <Eye className="w-3 h-3" />
      <span>View Only</span>
    </div>
  )
}

// Permission indicator showing current access level
export function PermissionIndicator({
  permissions,
  className = '',
}: {
  permissions: string[]
  className?: string
}) {
  const canWrite = permissions.includes('write')
  const canRead = permissions.includes('read')

  if (!canRead && !canWrite) {
    return (
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded-full bg-red-100 text-red-700 text-xs ${className}`}
      >
        <Lock className="w-3 h-3" />
        <span>No Access</span>
      </div>
    )
  }

  if (canWrite) {
    return (
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs ${className}`}
        title="You can edit this document"
      >
        <span className="w-2 h-2 rounded-full bg-green-500" />
        <span>Can Edit</span>
      </div>
    )
  }

  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-full bg-amber-100 text-amber-700 text-xs ${className}`}
      title="You have view-only access"
    >
      <Eye className="w-3 h-3" />
      <span>View Only</span>
    </div>
  )
}

export default ReadOnlyBanner
