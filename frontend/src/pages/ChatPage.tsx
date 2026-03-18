/**
 * ChatPage — full-width messaging layout (X1-031)
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useChatController } from '@/features/chat/useChatController'
import ChatSidebar from '@/features/chat/ChatSidebar'
import ChatView from '@/features/chat/ChatView'
import NewChatModal from '@/features/chat/NewChatModal'
import AddPeopleModal from '@/features/chat/AddPeopleModal'
import GroupSettingsModal from '@/features/chat/GroupSettingsModal'
import PageHeader from '@/components/PageHeader'

export default function ChatPage() {
  const [searchParams] = useSearchParams()
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const {
    chatsQuery,
    activeChatId,
    setActiveChatId,
    activeChatQuery,
    messagesQuery,
    filteredChats,
    searchFilter,
    setSearchFilter,
    typingText,
    isConnected,
    handleSend,
    handleTyping,
    handleDeleteChat,
    handleFileUpload,
    joinChat,
  } = useChatController()

  const [showNewChat, setShowNewChat] = useState(false)
  const [showAddPeople, setShowAddPeople] = useState(false)
  const [showGroupSettings, setShowGroupSettings] = useState(false)
  const [scrollToMessageId, setScrollToMessageId] = useState<number | null>(null)

  // Global cross-chat message search (debounced)
  const debouncedGlobalSearch = useDebouncedValue(searchFilter, 400)
  const globalSearchQuery = useQuery({
    queryKey: ['globalChatSearch', debouncedGlobalSearch],
    queryFn: () => api.searchAllChatMessages(debouncedGlobalSearch),
    enabled: debouncedGlobalSearch.length >= 2,
  })

  const handleSelectMessage = (chatId: number, messageId: number) => {
    setActiveChatId(chatId)
    joinChat(chatId)
    setScrollToMessageId(messageId)
  }

  // Mute toggle mutation (X1-025)
  const muteMutation = useMutation({
    mutationFn: (chatId: number) => api.toggleChatMute(chatId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', activeChatId] })
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  // Leave group mutation
  const leaveMutation = useMutation({
    mutationFn: (chatId: number) =>
      api.removeChatParticipant(chatId, currentUser!.id),
    onSuccess: () => {
      setActiveChatId(null)
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  // Auto-select chat from ?id= query parameter (e.g. from comment link)
  useEffect(() => {
    const idParam = searchParams.get('id')
    if (idParam) {
      const chatId = Number(idParam)
      if (chatId && !Number.isNaN(chatId)) {
        setActiveChatId(chatId)
        joinChat(chatId)
      }
    }
  }, [searchParams, setActiveChatId, joinChat])

  // Derive display name for the active chat
  const activeListItem = chatsQuery.data?.items?.find(
    (item) => item.chat.id === activeChatId,
  )
  const displayName = activeListItem?.display_name ?? 'Chat'

  const handleChatCreated = (chatId: number) => {
    setShowNewChat(false)
    setActiveChatId(chatId)
    joinChat(chatId)
  }

  const activeChat = activeChatQuery.data ?? null

  // Determine if the current user has muted this chat
  const isMuted = activeChat?.participants?.some(
    (p) => p.user_id === currentUser?.id && p.is_muted,
  ) ?? false

  const isGroup = activeChat?.type === 'group'

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <PageHeader
        title="Messages"
        subtitle="Private and group messaging"
      />

      <div className="flex flex-1 overflow-hidden rounded-xl border border-gray-200 bg-white mx-4 mb-4">
        {/* Sidebar — hidden on mobile when a chat is active */}
        <div className={`w-full md:w-80 flex-shrink-0 ${activeChatId ? 'hidden md:block' : ''}`}>
          <ChatSidebar
            chats={filteredChats}
            activeChatId={activeChatId}
            searchFilter={searchFilter}
            onSearchChange={setSearchFilter}
            onSelectChat={(id) => {
              setActiveChatId(id)
              joinChat(id)
            }}
            onNewChat={() => setShowNewChat(true)}
            globalSearchResults={debouncedGlobalSearch.length >= 2 ? globalSearchQuery.data?.items : undefined}
            globalSearchLoading={debouncedGlobalSearch.length >= 2 && globalSearchQuery.isLoading}
            onSelectMessage={handleSelectMessage}
          />
        </div>

        {/* Chat area — hidden on mobile when no chat selected */}
        <div className={`flex-1 ${!activeChatId ? 'hidden md:block' : ''}`}>
          <ChatView
            chat={activeChat}
            messages={messagesQuery.data?.items ?? []}
            displayName={displayName}
            typingText={typingText}
            isConnected={isConnected}
            isLoading={messagesQuery.isLoading}
            onSend={handleSend}
            onFileUpload={handleFileUpload}
            onTyping={handleTyping}
            onClose={() => setActiveChatId(null)}
            onDeleteChat={handleDeleteChat}
            onAddPeople={isGroup ? () => setShowAddPeople(true) : undefined}
            onMuteToggle={activeChatId ? () => muteMutation.mutate(activeChatId) : undefined}
            isMuted={isMuted}
            onLeaveChat={isGroup ? () => { if (activeChatId) leaveMutation.mutate(activeChatId) } : undefined}
            onOpenSettings={isGroup ? () => setShowGroupSettings(true) : undefined}
            scrollToMessageId={scrollToMessageId}
            onScrollToMessageHandled={() => setScrollToMessageId(null)}
          />
        </div>
      </div>

      {showNewChat && (
        <NewChatModal
          onClose={() => setShowNewChat(false)}
          onCreated={handleChatCreated}
        />
      )}

      {showAddPeople && activeChat && (
        <AddPeopleModal
          chat={activeChat}
          onClose={() => setShowAddPeople(false)}
        />
      )}

      {showGroupSettings && activeChat && (
        <GroupSettingsModal
          chat={activeChat}
          onClose={() => setShowGroupSettings(false)}
        />
      )}
    </div>
  )
}
