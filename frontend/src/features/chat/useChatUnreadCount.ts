/**
 * Hook to get total unread chat message count across all chats.
 * Used by Layout to show badge on Chat nav item.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useChatUnreadCount(): number {
  const { data } = useQuery({
    queryKey: ['chats'],
    queryFn: () => api.getChats(),
    refetchInterval: 30000,
    staleTime: 10000,
  })

  if (!data?.items) return 0
  return data.items.reduce((sum, item) => sum + (item.unread_count || 0), 0)
}
