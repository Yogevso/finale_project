import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { Bell, BellRing } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import { useToast } from '@/lib/toast'
import type { DocumentWatchStatus } from '@/types'

interface EngagementBarProps {
  documentId: number
  scrollProgress?: number // Real-time scroll progress from document preview
  isRevamp?: boolean
}

export default function EngagementBar({ documentId, scrollProgress, isRevamp = false }: EngagementBarProps) {
  const queryClient = useQueryClient()
  const lastSavedProgress = useRef<number>(0)
  const { isCustomer, isInternal } = useAuth()
  const toast = useToast()

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
    mutationFn: (nextWatching: boolean) =>
      nextWatching ? api.watchDocument(documentId) : api.unwatchDocument(documentId),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.documents.watchStatus(documentId) })

      const previousWatchStatus = queryClient.getQueryData<DocumentWatchStatus>(
        queryKeys.documents.watchStatus(documentId),
      )
      const nextWatching = !(previousWatchStatus?.is_watching ?? false)

      queryClient.setQueryData<DocumentWatchStatus>(
        queryKeys.documents.watchStatus(documentId),
        { is_watching: nextWatching },
      )

      return { previousWatchStatus }
    },
    onError: (_error, _variables, context) => {
      if (context?.previousWatchStatus) {
        queryClient.setQueryData(
          queryKeys.documents.watchStatus(documentId),
          context.previousWatchStatus,
        )
      } else {
        queryClient.removeQueries({ queryKey: queryKeys.documents.watchStatus(documentId) })
      }
      toast.error('Watch preference not updated', 'Please try again.')
    },
    onSuccess: (response) => {
      queryClient.setQueryData<DocumentWatchStatus>(
        queryKeys.documents.watchStatus(documentId),
        { is_watching: response.is_watching },
      )
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.watchStatus(documentId) })
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
    <div
      className={`document-detail-engagement border bg-white ${
        isRevamp
          ? 'rounded-2xl px-4 py-3 shadow-[0_10px_24px_-18px_rgba(15,23,42,0.35)]'
          : 'mb-6 rounded-xl p-4 shadow-sm'
      }`}
    >
      <div className={`flex flex-wrap items-center ${isRevamp ? 'gap-3' : 'gap-6'}`}>
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
            onClick={() => toggleWatch.mutate(!(watchStatus?.is_watching ?? false))}
            disabled={toggleWatch.isPending}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              watchStatus?.is_watching
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
            }`}
            aria-pressed={watchStatus?.is_watching ?? false}
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
                    displayProgress >= 100 ? 'bg-emerald-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${displayProgress}%` }}
                />
              </div>
              <span className={`text-sm font-medium min-w-[3rem] ${
                displayProgress >= 100 ? 'text-emerald-600' : 'text-blue-600'
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
