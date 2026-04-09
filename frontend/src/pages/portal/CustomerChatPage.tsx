/**
 * CustomerChatPage - customer access to existing customer/internal conversations.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import PageHeader from '@/components/PageHeader'
import ChatSidebar from '@/features/chat/ChatSidebar'
import ChatView from '@/features/chat/ChatView'
import { useChatSocket } from '@/hooks/useChatSocket'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useToast } from '@/lib/toast'
import type { ChatListItem, ChatMessage } from '@/types/chat'

export default function CustomerChatPage() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const toast = useToast()
  const [activeChatId, setActiveChatId] = useState<number | null>(null)
  const [searchFilter, setSearchFilter] = useState('')
  const [typingUsers, setTypingUsers] = useState<Record<number, { username: string; timeout: ReturnType<typeof setTimeout> }>>({})
  const optimisticIdCounter = useRef(0)

  const chatsQuery = useQuery({
    queryKey: ['portalChats'],
    queryFn: () => api.getPortalChats(),
    refetchInterval: 30000,
  })

  const activeChatQuery = useQuery({
    queryKey: ['portalChat', activeChatId],
    queryFn: () => (activeChatId ? api.getPortalChatDetail(activeChatId) : Promise.reject()),
    enabled: !!activeChatId,
  })

  const messagesQuery = useQuery({
    queryKey: ['portalChatMessages', activeChatId],
    queryFn: () => (activeChatId ? api.getPortalChatMessages(activeChatId) : Promise.reject()),
    enabled: !!activeChatId,
  })

  const socket = useChatSocket({
    enabled: true,
    onNewMessage: useCallback(
      (message: ChatMessage) => {
        if (message.chat_id === activeChatId) {
          queryClient.setQueryData<{ items: ChatMessage[]; has_more: boolean }>(
            ['portalChatMessages', activeChatId],
            (current) => {
              if (!current) return { items: [message], has_more: false }
              if (current.items.some((item) => item.id === message.id)) return current
              const optimisticIndex = current.items.findIndex(
                (item) => item.id < 0 && item.sender_id === message.sender_id && item.content === message.content,
              )
              if (optimisticIndex >= 0) {
                const nextItems = [...current.items]
                nextItems[optimisticIndex] = message
                return { ...current, items: nextItems }
              }
              return { ...current, items: [message, ...current.items] }
            },
          )
        }
        void queryClient.invalidateQueries({ queryKey: ['portalChats'] })
      },
      [activeChatId, queryClient],
    ),
    onUserTyping: useCallback(
      (data: { chat_id: number; user_id: number; username: string }) => {
        if (data.chat_id !== activeChatId) {
          return
        }
        setTypingUsers((previous) => {
          if (previous[data.user_id]) {
            clearTimeout(previous[data.user_id].timeout)
          }
          const timeout = setTimeout(() => {
            setTypingUsers((current) => {
              const next = { ...current }
              delete next[data.user_id]
              return next
            })
          }, 3000)
          return { ...previous, [data.user_id]: { username: data.username, timeout } }
        })
      },
      [activeChatId],
    ),
  })

  useEffect(() => {
    if (!activeChatId || !socket.isConnected) {
      return
    }

    socket.joinChat(activeChatId)
    socket.markRead(activeChatId)
    void api.markPortalChatAsRead(activeChatId)
    void queryClient.invalidateQueries({ queryKey: ['portalChats'] })
  }, [activeChatId, queryClient, socket])

  const filteredChats = useMemo(() => {
    const items = chatsQuery.data?.items ?? []
    if (!searchFilter) return items
    const lower = searchFilter.toLowerCase()
    return items.filter((item: ChatListItem) => item.display_name.toLowerCase().includes(lower))
  }, [chatsQuery.data, searchFilter])

  const typingText = useMemo(() => {
    const names = Object.values(typingUsers).map((entry) => entry.username)
    if (names.length === 0) return ''
    if (names.length === 1) return `${names[0]} is typing...`
    return `${names.join(', ')} are typing...`
  }, [typingUsers])

  const handleSend = useCallback(
    (content: string) => {
      if (!activeChatId || !content.trim() || !currentUser) {
        return
      }

      optimisticIdCounter.current -= 1
      const optimistic: ChatMessage = {
        id: optimisticIdCounter.current,
        chat_id: activeChatId,
        sender_id: currentUser.id,
        sender_full_name: currentUser.full_name,
        content: content.trim(),
        message_type: 'text',
        file_url: null,
        file_name: null,
        file_mime_type: null,
        file_size: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      queryClient.setQueryData<{ items: ChatMessage[]; has_more: boolean }>(
        ['portalChatMessages', activeChatId],
        (current) => {
          if (!current) return { items: [optimistic], has_more: false }
          return { ...current, items: [optimistic, ...current.items] }
        },
      )

      try {
        socket.sendMessage(activeChatId, content)
      } catch {
        void queryClient.invalidateQueries({ queryKey: ['portalChatMessages', activeChatId] })
        toast.error('Failed to send message', 'Please check your connection and try again.')
      }
    },
    [activeChatId, currentUser, queryClient, socket, toast],
  )

  const handleTyping = useCallback(() => {
    if (activeChatId) {
      socket.sendTyping(activeChatId)
    }
  }, [activeChatId, socket])

  const displayName = chatsQuery.data?.items?.find((item) => item.chat.id === activeChatId)?.display_name ?? 'Conversation'

  return (
    <div className="page-stack flex h-[calc(100vh-9rem)] flex-col">
      <PageHeader
        eyebrow="Customer Portal"
        title="Messages"
        subtitle="Direct conversations with your team. Support tickets and escalated feedback conversations stay in Support."
      />

      <div className="surface-card flex flex-1 overflow-hidden rounded-2xl">
        <div className={`w-full md:w-80 flex-shrink-0 ${activeChatId ? 'hidden md:block' : ''}`}>
          <ChatSidebar
            chats={filteredChats}
            activeChatId={activeChatId}
            searchFilter={searchFilter}
            onSearchChange={setSearchFilter}
            onSelectChat={(chatId) => {
              setActiveChatId(chatId)
              socket.joinChat(chatId)
            }}
            isLoading={chatsQuery.isLoading}
            isError={chatsQuery.isError}
            onRetry={() => void chatsQuery.refetch()}
            showNewChatButton={false}
          />
        </div>

        <div className={`flex-1 ${!activeChatId ? 'hidden md:block' : ''}`}>
          <ChatView
            chat={activeChatQuery.data ?? null}
            messages={messagesQuery.data?.items ?? []}
            displayName={displayName}
            typingText={typingText}
            isConnected={socket.isConnected}
            isLoading={messagesQuery.isLoading}
            isError={messagesQuery.isError}
            onRetry={() => void messagesQuery.refetch()}
            onSend={handleSend}
            onTyping={handleTyping}
            onClose={() => setActiveChatId(null)}
          />
        </div>
      </div>
    </div>
  )
}
