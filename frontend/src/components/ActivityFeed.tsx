/**
 * ActivityFeed Component
 *
 * Displays a real-time feed of collaboration activities for a document.
 * Shows who joined/left, edits made, and other collaboration events.
 */

import { useEffect, useState, useCallback } from 'react'
import {
  Users,
  Edit3,
  LogIn,
  LogOut,
  Save,
  MessageSquare,
  Clock,
  RefreshCw,
  ChevronDown,
  Activity,
} from 'lucide-react'
import { api } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'

// Activity types from backend (for reference)
// 'session_start' | 'session_end' | 'user_joined' | 'user_left' | 'content_edited'
// | 'cursor_moved' | 'selection_changed' | 'version_created' | 'comment_added'

interface ActivityItem {
  id: number
  document_id: number
  user_id: number
  username: string
  activity_type: string // Keep as string since API returns string
  details: Record<string, unknown> | null
  created_at: string
}

interface ActivityFeedProps {
  documentId: number
  className?: string
  autoRefresh?: boolean
  refreshInterval?: number // in milliseconds
  maxItems?: number
  compact?: boolean
}

// Get icon for activity type
function getActivityIcon(type: string) {
  switch (type) {
    case 'session_start':
    case 'user_joined':
      return <LogIn className="w-4 h-4 text-emerald-500" />
    case 'session_end':
    case 'user_left':
      return <LogOut className="w-4 h-4 text-slate-500" />
    case 'content_edited':
      return <Edit3 className="w-4 h-4 text-sky-500" />
    case 'version_created':
      return <Save className="w-4 h-4 text-purple-500" />
    case 'comment_added':
      return <MessageSquare className="w-4 h-4 text-amber-500" />
    case 'cursor_moved':
    case 'selection_changed':
      return <Users className="w-4 h-4 text-slate-400" />
    default:
      return <Activity className="w-4 h-4 text-slate-400" />
  }
}

// Get human-readable description for activity
function getActivityDescription(activity: ActivityItem): string {
  const { activity_type, username, details } = activity

  switch (activity_type) {
    case 'session_start':
    case 'user_joined':
      return `${username} joined the document`
    case 'session_end':
    case 'user_left': {
      const duration = details?.duration_seconds as number | undefined
      const edits = details?.edits_count as number | undefined
      if (duration && edits !== undefined) {
        const mins = Math.floor(duration / 60)
        return `${username} left after ${mins}m with ${edits} edit${edits !== 1 ? 's' : ''}`
      }
      return `${username} left the document`
    }
    case 'content_edited':
      return `${username} made an edit`
    case 'version_created':
      return `${username} created a new version`
    case 'comment_added':
      return `${username} added a comment`
    case 'cursor_moved':
      return `${username} is viewing`
    case 'selection_changed':
      return `${username} selected text`
    default:
      return `${username} performed an action`
  }
}

// Single activity item component
function ActivityItemRow({
  activity,
  compact,
}: {
  activity: ActivityItem
  compact: boolean
}) {
  const timeAgo = formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })

  if (compact) {
    return (
      <div className="flex items-center gap-2 py-1 px-2 text-sm">
        {getActivityIcon(activity.activity_type)}
        <span className="truncate flex-1">{getActivityDescription(activity)}</span>
        <span className="text-xs text-slate-400 whitespace-nowrap">{timeAgo}</span>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 p-3 hover:bg-slate-50 transition-colors">
      <div className="mt-0.5">{getActivityIcon(activity.activity_type)}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-900">{getActivityDescription(activity)}</p>
        <div className="flex items-center gap-2 mt-1">
          <Clock className="w-3 h-3 text-slate-400" />
          <span className="text-xs text-slate-500">{timeAgo}</span>
        </div>
      </div>
    </div>
  )
}

export function ActivityFeed({
  documentId,
  className = '',
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
  maxItems = 50,
  compact = false,
}: ActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)

  const fetchActivities = useCallback(async () => {
    try {
      const response = await api.getActivityFeed(documentId, maxItems, 0)
      setActivities(response.activities)
      setHasMore(response.has_more)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch activities:', err)
      setError('Failed to load activity feed')
    } finally {
      setLoading(false)
    }
  }, [documentId, maxItems])

  // Initial fetch
  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(fetchActivities, refreshInterval)
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, fetchActivities])

  const loadMore = async () => {
    try {
      const response = await api.getActivityFeed(documentId, maxItems, activities.length)
      setActivities((prev) => [...prev, ...response.activities])
      setHasMore(response.has_more)
    } catch (err) {
      console.error('Failed to load more activities:', err)
    }
  }

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-slate-200 ${className}`}>
        <div className="p-4 text-center text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
          <span className="text-sm">Loading activity...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white rounded-xl border border-slate-200 ${className}`}>
        <div className="p-4 text-center">
          <p className="text-sm text-rose-600">{error}</p>
          <button
            onClick={fetchActivities}
            className="mt-2 text-sm text-sky-600 hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white rounded-xl border border-slate-200 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 border-b border-slate-200 cursor-pointer hover:bg-slate-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-slate-600" />
          <span className="font-medium text-sm text-slate-900">Activity Feed</span>
          <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
            {activities.length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              fetchActivities()
            }}
            className="p-1 hover:bg-slate-200 rounded"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-slate-500" />
          </button>
          <ChevronDown
            className={`w-4 h-4 text-slate-500 transition-transform ${
              isExpanded ? '' : '-rotate-90'
            }`}
          />
        </div>
      </div>

      {/* Activity list */}
      {isExpanded && (
        <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
          {activities.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-sm">
              No activity yet
            </div>
          ) : (
            <>
              {activities.map((activity) => (
                <ActivityItemRow
                  key={activity.id}
                  activity={activity}
                  compact={compact}
                />
              ))}
              {hasMore && (
                <button
                  onClick={loadMore}
                  className="w-full p-2 text-center text-sm text-sky-600 hover:bg-slate-50"
                >
                  Load more
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// Compact inline version for toolbars
export function ActivityFeedCompact({
  documentId,
  className = '',
}: {
  documentId: number
  className?: string
}) {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [showDropdown, setShowDropdown] = useState(false)

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const response = await api.getActivityFeed(documentId, 5, 0)
        setActivities(response.activities)
      } catch (err) {
        console.error('Failed to fetch recent activities:', err)
      }
    }
    fetchRecent()
    const interval = setInterval(fetchRecent, 30000)
    return () => clearInterval(interval)
  }, [documentId])

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-1 px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 rounded"
      >
        <Activity className="w-4 h-4" />
        <span className="hidden sm:inline">Activity</span>
        {activities.length > 0 && (
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
        )}
      </button>

      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />
          <div className="absolute right-0 top-full mt-1 w-72 bg-white rounded-xl shadow-lg border border-slate-200 z-20">
            <div className="p-2 border-b border-slate-100">
              <span className="text-sm font-medium text-slate-900">Recent Activity</span>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {activities.length === 0 ? (
                <div className="p-3 text-center text-sm text-slate-500">
                  No recent activity
                </div>
              ) : (
                activities.map((activity) => (
                  <ActivityItemRow
                    key={activity.id}
                    activity={activity}
                    compact={true}
                  />
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ActivityFeed
