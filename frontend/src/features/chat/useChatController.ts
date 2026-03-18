/**
 * Chat feature — controller hook for business logic (Wave X.1)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useChatSocket } from '@/hooks/useChatSocket'
import { useToast } from '@/lib/toast'
import type {
  ChatListItem,
  ChatMessage,
} from '@/types/chat'

export function useChatController() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [activeChatId, setActiveChatId] = useState<number | null>(null)
  const [searchFilter, setSearchFilter] = useState('')
  const [typingUsers, setTypingUsers] = useState<Record<number, { username: string; timeout: ReturnType<typeof setTimeout> }>>({})
  const optimisticIdCounter = useRef(0)
  const toast = useToast()

  // Fetch chat list
  const chatsQuery = useQuery({
    queryKey: ['chats'],
    queryFn: () => api.getChats(),
    refetchInterval: 30000, // Refresh every 30s as fallback
  })

  // Fetch active chat detail
  const activeChatQuery = useQuery({
    queryKey: ['chat', activeChatId],
    queryFn: () => (activeChatId ? api.getChatDetail(activeChatId) : Promise.reject()),
    enabled: !!activeChatId,
  })

  // Fetch messages for active chat
  const messagesQuery = useQuery({
    queryKey: ['chatMessages', activeChatId],
    queryFn: () => (activeChatId ? api.getChatMessages(activeChatId) : Promise.reject()),
    enabled: !!activeChatId,
  })

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: ({ chatId, content }: { chatId: number; content: string }) =>
      api.sendChatMessage(chatId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeChatId] })
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  // Delete chat mutation
  const deleteChatMutation = useMutation({
    mutationFn: (chatId: number) => api.deleteChat(chatId),
    onSuccess: () => {
      setActiveChatId(null)
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  // Upload file mutation
  const uploadFileMutation = useMutation({
    mutationFn: ({ chatId, file }: { chatId: number; file: File }) =>
      api.uploadChatFile(chatId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeChatId] })
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  // WebSocket for real-time updates
  const socket = useChatSocket({
    enabled: true,
    onNewMessage: useCallback(
      (message: ChatMessage) => {
        // Add message to active chat instantly
        if (message.chat_id === activeChatId) {
          queryClient.setQueryData<{ items: ChatMessage[]; has_more: boolean }>(
            ['chatMessages', activeChatId],
            (old) => {
              if (!old) return { items: [message], has_more: false }
              // Avoid duplicates
              if (old.items.some((m) => m.id === message.id)) return old
              // Replace optimistic message from same sender with same content
              const optimisticIdx = old.items.findIndex(
                (m) => m.id < 0 && m.sender_id === message.sender_id && m.content === message.content,
              )
              if (optimisticIdx >= 0) {
                const updated = [...old.items]
                updated[optimisticIdx] = message
                return { ...old, items: updated }
              }
              return { ...old, items: [message, ...old.items] }
            },
          )
        }
        // Refresh chat list for unread counts
        queryClient.invalidateQueries({ queryKey: ['chats'] })
      },
      [activeChatId, queryClient],
    ),
    onUserTyping: useCallback(
      (data: { chat_id: number; user_id: number; username: string }) => {
        setTypingUsers((prev) => {
          // Clear existing timeout
          if (prev[data.user_id]) {
            clearTimeout(prev[data.user_id].timeout)
          }
          // 3-second debounce
          const timeout = setTimeout(() => {
            setTypingUsers((p) => {
              const next = { ...p }
              delete next[data.user_id]
              return next
            })
          }, 3000)
          return { ...prev, [data.user_id]: { username: data.username, timeout } }
        })
      },
      [],
    ),
  })

  // Mark chat as read when opening
  useEffect(() => {
    if (activeChatId && socket.isConnected) {
      socket.markRead(activeChatId)
    }
  }, [activeChatId, socket])

  // Filtered chat list
  const filteredChats = useMemo(() => {
    const items = chatsQuery.data?.items ?? []
    if (!searchFilter) return items
    const lower = searchFilter.toLowerCase()
    return items.filter((item: ChatListItem) =>
      item.display_name.toLowerCase().includes(lower),
    )
  }, [chatsQuery.data, searchFilter])

  // Typing indicator text for active chat
  const typingText = useMemo(() => {
    const typingInChat = Object.values(typingUsers).map((t) => t.username)
    if (typingInChat.length === 0) return ''
    if (typingInChat.length === 1) return `${typingInChat[0]} is typing...`
    return `${typingInChat.join(', ')} are typing...`
  }, [typingUsers])

  const handleSend = useCallback(
    (content: string) => {
      if (!activeChatId || !content.trim()) return

      // Optimistic insert (X1-035): show message immediately
      if (currentUser) {
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
          ['chatMessages', activeChatId],
          (old) => {
            if (!old) return { items: [optimistic], has_more: false }
            return { ...old, items: [optimistic, ...old.items] }
          },
        )
      }

      // Send via WebSocket — the server persists the message and broadcasts it back
      try {
        socket.sendMessage(activeChatId, content)
      } catch {
        // Remove optimistic message on send failure
        queryClient.invalidateQueries({ queryKey: ['chatMessages', activeChatId] })
        toast.error('Failed to send message', 'Please check your connection and try again.')
      }
    },
    [activeChatId, socket, currentUser, queryClient, toast],
  )

  const handleTyping = useCallback(() => {
    if (activeChatId) {
      socket.sendTyping(activeChatId)
    }
  }, [activeChatId, socket])

  const handleDeleteChat = useCallback(() => {
    if (activeChatId) {
      deleteChatMutation.mutate(activeChatId)
    }
  }, [activeChatId, deleteChatMutation])

  const handleFileUpload = useCallback(
    (file: File) => {
      if (!activeChatId) return
      uploadFileMutation.mutate({ chatId: activeChatId, file })
    },
    [activeChatId, uploadFileMutation],
  )

  return {
    chatsQuery,
    activeChatId,
    setActiveChatId,
    activeChatQuery,
    messagesQuery,
    filteredChats,
    searchFilter,
    setSearchFilter,
    typingText,
    isConnected: socket.isConnected,
    handleSend,
    handleTyping,
    handleDeleteChat,
    handleFileUpload,
    sendMessageMutation,
    joinChat: socket.joinChat,
  }
}
