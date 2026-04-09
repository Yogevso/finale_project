/**
 * Hook to get total unread chat message count across all chats.
 * Used by navigation shells to show badge on chat nav items.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useChatUnreadCount(scope: 'internal' | 'portal' = 'internal'): number {
  const { data } = useQuery({
    queryKey: [scope, 'chats'],
    queryFn: () => (scope === 'portal' ? api.getPortalChats() : api.getChats()),
    refetchInterval: 30000,
    staleTime: 10000,
  })

  if (!data?.items) return 0
  return data.items.reduce((sum, item) => sum + (item.unread_count || 0), 0)
}
