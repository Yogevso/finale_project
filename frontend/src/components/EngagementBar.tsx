import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { api } from '@/lib/api'

interface EngagementBarProps {
  documentId: number
  scrollProgress?: number // Real-time scroll progress from document preview
}

export default function EngagementBar({ documentId, scrollProgress }: EngagementBarProps) {
  const queryClient = useQueryClient()
  const lastSavedProgress = useRef<number>(0)

  // Bookmark status
  const { data: bookmarkStatus } = useQuery({
    queryKey: ['bookmark-status', documentId],
    queryFn: () => api.checkBookmarkStatus(documentId),
  })

  // Feedback status
  const { data: feedbackStats } = useQuery({
    queryKey: ['feedback-stats', documentId],
    queryFn: () => api.getFeedbackStats(documentId),
  })

  const { data: myFeedback } = useQuery({
    queryKey: ['my-feedback', documentId],
    queryFn: () => api.getMyFeedback(documentId),
  })

  // Reading progress
  const { data: progress } = useQuery({
    queryKey: ['reading-progress', documentId],
    queryFn: () => api.getDocumentProgress(documentId),
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

  const submitFeedback = useMutation({
    mutationFn: (isHelpful: boolean) => api.submitFeedback(documentId, isHelpful),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-feedback', documentId] })
      queryClient.invalidateQueries({ queryKey: ['feedback-stats', documentId] })
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
  }, [scrollProgress, progress?.progress_percent])

  // Use scrollProgress if available, otherwise fall back to saved progress
  const displayProgress = scrollProgress !== undefined 
    ? Math.max(scrollProgress, progress?.progress_percent || 0)
    : (progress?.progress_percent || 0)

  return (
    <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
      <div className="flex flex-wrap items-center gap-6">
        {/* Bookmark */}
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

        {/* Feedback */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">Was this helpful?</span>
          <button
            onClick={() => submitFeedback.mutate(true)}
            disabled={submitFeedback.isPending}
            className={`px-3 py-1 rounded-xl text-sm flex items-center gap-1 ${
              myFeedback?.is_helpful === true
                ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            👍 <span className="hidden sm:inline">Yes</span>
            {feedbackStats?.helpful_count > 0 && (
              <span className="ml-1 text-xs">({feedbackStats.helpful_count})</span>
            )}
          </button>
          <button
            onClick={() => submitFeedback.mutate(false)}
            disabled={submitFeedback.isPending}
            className={`px-3 py-1 rounded-xl text-sm flex items-center gap-1 ${
              myFeedback?.is_helpful === false
                ? 'bg-rose-100 text-rose-700 border border-rose-200'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            👎 <span className="hidden sm:inline">No</span>
            {feedbackStats?.not_helpful_count > 0 && (
              <span className="ml-1 text-xs">({feedbackStats.not_helpful_count})</span>
            )}
          </button>
        </div>

        {/* Reading Progress */}
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
      </div>
    </div>
  )
}
