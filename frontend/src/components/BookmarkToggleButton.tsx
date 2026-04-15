import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Star } from 'lucide-react'
import { api } from '@/lib/api'

type BookmarkToggleButtonProps = {
  documentId: number
  documentTitle?: string
  showLabel?: boolean
  className?: string
}

export default function BookmarkToggleButton({
  documentId,
  documentTitle,
  showLabel = true,
  className = '',
}: BookmarkToggleButtonProps) {
  const queryClient = useQueryClient()
  const queryKey = ['bookmark-status', documentId] as const

  const bookmarkStatusQuery = useQuery({
    queryKey,
    queryFn: () => api.checkBookmarkStatus(documentId),
  })

  const toggleBookmarkMutation = useMutation({
    mutationFn: async () => {
      if (bookmarkStatusQuery.data?.is_bookmarked) {
        await api.removeBookmark(documentId)
        return false
      }
      await api.addBookmark(documentId)
      return true
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey })
      const previousValue = queryClient.getQueryData<{ is_bookmarked: boolean }>(queryKey)
      queryClient.setQueryData(queryKey, {
        is_bookmarked: !previousValue?.is_bookmarked,
      })
      return { previousValue }
    },
    onError: (_error, _variables, context) => {
      if (context?.previousValue) {
        queryClient.setQueryData(queryKey, context.previousValue)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
      queryClient.invalidateQueries({ queryKey: ['bookmarks', 'dashboard'] })
    },
  })

  const isBookmarked = bookmarkStatusQuery.data?.is_bookmarked ?? false
  const accessibleLabel = documentTitle
    ? `${isBookmarked ? 'Remove bookmark from' : 'Add bookmark to'} ${documentTitle}`
    : isBookmarked
      ? 'Remove bookmark'
      : 'Add bookmark'

  return (
    <button
      type="button"
      onClick={() => toggleBookmarkMutation.mutate()}
      disabled={bookmarkStatusQuery.isLoading || toggleBookmarkMutation.isPending}
      aria-pressed={isBookmarked}
      aria-label={!showLabel ? accessibleLabel : undefined}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition hover:scale-[1.02] disabled:opacity-60 ${
        isBookmarked
          ? 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100'
          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
      } ${className}`}
      title={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
    >
      <span key={isBookmarked ? 'saved' : 'unsaved'} className="motion-enter-scale inline-flex items-center gap-2">
        <Star className={`h-4 w-4 ${isBookmarked ? 'fill-current' : ''}`} />
        {showLabel ? <span>{isBookmarked ? 'In My Activities' : 'Add to My Activities'}</span> : null}
      </span>
    </button>
  )
}
