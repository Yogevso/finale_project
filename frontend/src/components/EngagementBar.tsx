import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { Bell, BellRing } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'

interface EngagementBarProps {
  documentId: number
  scrollProgress?: number // Real-time scroll progress from document preview
}

export default function EngagementBar({ documentId, scrollProgress }: EngagementBarProps) {
  const queryClient = useQueryClient()
  const lastSavedProgress = useRef<number>(0)
  const { isCustomer, isInternal } = useAuth()

  // Bookmark status
  const { data: bookmarkStatus } = useQuery({
    queryKey: ['bookmark-status', documentId],
    queryFn: () => api.checkBookmarkStatus(documentId),
    enabled: isCustomer,
  })

  const { data: watchStatus } = useQuery({
    queryKey: queryKeys.documents.watchStatus(documentId),
    queryFn: () => api.getDocumentWatchStatus(documentId),
    enabled: isInternal,
  })

  // Reading progress
  const { data: progress } = useQuery({
    queryKey: ['reading-progress', documentId],
    queryFn: () => api.getDocumentProgress(documentId),
    enabled: isCustomer,
  })

  // Mutations
  const toggleBookmark = useMutation({
    mutationFn: () => 
      bookmarkStatus?.is_bookmarked 
        ? api.removeBookmark(documentId)
        : api.addBookmark(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmark-status', documentId] })
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
    },
  })

  const toggleWatch = useMutation({
    mutationFn: () =>
      watchStatus?.is_watching ? api.unwatchDocument(documentId) : api.watchDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.watchStatus(documentId) })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const updateProgress = useMutation({
    mutationFn: (percent: number) => api.updateReadingProgress(documentId, percent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reading-progress', documentId] })
    },
  })

  // Auto-save progress when scrollProgress increases significantly
  useEffect(() => {
    if (!isCustomer) {
      return
    }
    if (scrollProgress !== undefined && scrollProgress > lastSavedProgress.current) {
      // Save progress at 25%, 50%, 75%, 100% milestones or when reaching new 10% increments
      const savedProgress = progress?.progress_percent || 0
      const currentMilestone = Math.floor(scrollProgress / 10) * 10
      const savedMilestone = Math.floor(savedProgress / 10) * 10
      
      if (currentMilestone > savedMilestone && scrollProgress > savedProgress) {
        lastSavedProgress.current = scrollProgress
        updateProgress.mutate(Math.round(scrollProgress))
      }
    }
  }, [isCustomer, progress?.progress_percent, scrollProgress, updateProgress])

  // Use scrollProgress if available, otherwise fall back to saved progress
  const displayProgress = scrollProgress !== undefined 
    ? Math.max(scrollProgress, progress?.progress_percent || 0)
    : (progress?.progress_percent || 0)

  return (
    <div className="document-detail-engagement bg-white rounded-xl shadow-sm border p-4 mb-6">
      <div className="flex flex-wrap items-center gap-6">
        {/* Bookmark */}
        {isCustomer && (
          <button
            onClick={() => toggleBookmark.mutate()}
            disabled={toggleBookmark.isPending}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              bookmarkStatus?.is_bookmarked
                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            <span>{bookmarkStatus?.is_bookmarked ? '★' : '☆'}</span>
            <span className="text-sm font-medium">
              {bookmarkStatus?.is_bookmarked ? 'Bookmarked' : 'Bookmark'}
            </span>
          </button>
        )}

        {isInternal && (
          <button
            onClick={() => toggleWatch.mutate()}
            disabled={toggleWatch.isPending}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              watchStatus?.is_watching
                ? 'bg-sky-50 text-sky-700 border border-sky-200'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            {watchStatus?.is_watching ? (
              <BellRing className="h-4 w-4" />
            ) : (
              <Bell className="h-4 w-4" />
            )}
            <span className="text-sm font-medium">
              {watchStatus?.is_watching ? 'Following updates' : 'Follow updates'}
            </span>
          </button>
        )}

        {/* Reading Progress */}
        {isCustomer && (
          <div className="flex items-center gap-3 ml-auto">
            <span className="text-sm text-slate-500">Reading:</span>
            <div className="flex items-center gap-2">
              <div className="w-32 h-2.5 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    displayProgress >= 100 ? 'bg-emerald-500' : 'bg-sky-500'
                  }`}
                  style={{ width: `${displayProgress}%` }}
                />
              </div>
              <span className={`text-sm font-medium min-w-[3rem] ${
                displayProgress >= 100 ? 'text-emerald-600' : 'text-sky-600'
              }`}>
                {Math.round(displayProgress)}%
              </span>
            </div>
            {displayProgress >= 100 && (
              <span className="text-emerald-600 text-sm">✓ Complete</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
