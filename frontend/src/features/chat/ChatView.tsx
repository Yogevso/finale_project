/**
 * ChatView — message list + header + input for the active chat (X1-028)
 */

import { useRef, useEffect, useMemo, useState } from 'react'
import { MessageCircle, Search, X, ChevronUp, ChevronDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { MessageSkeleton } from '@/components/skeletons'
import type { ChatDetail, ChatMessage as ChatMessageType } from '@/types/chat'
import ChatHeader from './ChatHeader'
import ChatMessageBubble from './ChatMessage'
import MessageInput from './MessageInput'

interface ChatViewProps {
  chat: ChatDetail | null
  messages: ChatMessageType[]
  displayName: string
  typingText: string
  isConnected: boolean
  isLoading: boolean
  isError?: boolean
  onRetry?: () => void
  onSend: (content: string) => void
  onFileUpload?: (file: File) => void
  onTyping: () => void
  onClose: () => void
  onDeleteChat?: () => void
  onAddPeople?: () => void
  onMuteToggle?: () => void
  isMuted?: boolean
  onLeaveChat?: () => void
  onOpenSettings?: () => void
  scrollToMessageId?: number | null
  onScrollToMessageHandled?: () => void
}

export default function ChatView({
  chat,
  messages,
  displayName,
  typingText,
  isConnected,
  isLoading,
  isError = false,
  onRetry,
  onSend,
  onFileUpload,
  onTyping,
  onClose,
  onDeleteChat,
  onAddPeople,
  onMuteToggle,
  isMuted,
  onLeaveChat,
  onOpenSettings,
  scrollToMessageId,
  onScrollToMessageHandled,
}: ChatViewProps) {
  const { user } = useAuth()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [showSearch, setShowSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeResultIndex, setActiveResultIndex] = useState(0)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const debouncedSearch = useDebouncedValue(searchQuery, 300)

  const searchResults = useQuery({
    queryKey: ['chatSearch', chat?.id, debouncedSearch, messages.length],
    queryFn: () => (chat ? api.searchChatMessages(chat.id, debouncedSearch) : Promise.reject()),
    enabled: !!chat && debouncedSearch.length > 0,
  })

  // Ordered list of matching message IDs (chronological in the view = reversed API order)
  const matchedIds = useMemo(() => {
    if (!debouncedSearch || !searchResults.data) return [] as number[]
    // API returns newest-first; messages are displayed reversed (oldest-first)
    return [...searchResults.data.items].reverse().map((m) => m.id)
  }, [debouncedSearch, searchResults.data])

  const highlightIds = useMemo(() => new Set(matchedIds), [matchedIds])

  // Reset index to first result whenever results change
  useEffect(() => {
    setActiveResultIndex(0)
  }, [matchedIds.length, debouncedSearch])

  // Scroll to the active result
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (matchedIds.length === 0 || !scrollContainerRef.current) return
    const activeId = matchedIds[activeResultIndex]
    if (activeId == null) return
    const el = scrollContainerRef.current.querySelector(`[data-msg-id="${activeId}"]`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [activeResultIndex, matchedIds])

  // Scroll to a specific message (from global search)
  useEffect(() => {
    if (!scrollToMessageId || !scrollContainerRef.current) return
    const el = scrollContainerRef.current.querySelector(`[data-msg-id="${scrollToMessageId}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      // Flash highlight
      el.classList.add('ring-2', 'ring-yellow-400', 'rounded-2xl', 'bg-yellow-50/50')
      const timer = setTimeout(() => {
        el.classList.remove('ring-2', 'ring-yellow-400', 'rounded-2xl', 'bg-yellow-50/50')
      }, 2000)
      onScrollToMessageHandled?.()
      return () => clearTimeout(timer)
    }
    onScrollToMessageHandled?.()
  }, [scrollToMessageId, messages, onScrollToMessageHandled])

  // Compute the latest last_read_at among other participants (for read receipts)
  const othersLastRead = useMemo(() => {
    if (!chat || !user) return null
    const others = chat.participants.filter((p) => p.user_id !== user.id)
    if (others.length === 0) return null
    const times = others
      .map((p) => p.last_read_at)
      .filter(Boolean)
      .map((t) => new Date(t!).getTime())
    return times.length > 0 ? Math.max(...times) : null
  }, [chat, user])

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  useEffect(() => {
    if (showSearch) {
      searchInputRef.current?.focus()
    }
  }, [showSearch])

  if (!chat) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-50 p-6 dark:bg-slate-950">
        <EmptyState
          icon={<MessageCircle className="h-8 w-8" aria-hidden="true" />}
          title="Select a conversation"
          description="Choose a chat from the sidebar or start a new one."
          className="w-full max-w-md"
        />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <ChatHeader
        chat={chat}
        displayName={displayName}
        typingText={typingText}
        isConnected={isConnected}
        onClose={onClose}
        onDeleteChat={onDeleteChat}
        onAddPeople={onAddPeople}
        onMuteToggle={onMuteToggle}
        isMuted={isMuted}
        onLeaveChat={onLeaveChat}
        onSearch={() => setShowSearch(!showSearch)}
        onOpenSettings={onOpenSettings}
      />

      {/* Search bar (X1-043) */}
      {showSearch && (
        <div className="flex items-center gap-2 border-b border-gray-200 bg-white px-4 py-2">
          <Search className="h-4 w-4 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none"
          />
          {debouncedSearch && matchedIds.length > 0 && (
            <span className="text-xs text-gray-500 tabular-nums">
              {activeResultIndex + 1}/{matchedIds.length}
            </span>
          )}
          {debouncedSearch && matchedIds.length === 0 && !searchResults.isLoading && (
            <span className="text-xs text-gray-400">No results</span>
          )}
          <button
            type="button"
            onClick={() => setActiveResultIndex((i) => (i > 0 ? i - 1 : matchedIds.length - 1))}
            disabled={matchedIds.length === 0}
            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30"
            title="Previous result"
            aria-label="Go to previous search result"
          >
            <ChevronUp className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setActiveResultIndex((i) => (i < matchedIds.length - 1 ? i + 1 : 0))}
            disabled={matchedIds.length === 0}
            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30"
            title="Next result"
            aria-label="Go to next search result"
          >
            <ChevronDown className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => { setShowSearch(false); setSearchQuery('') }}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close message search"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollContainerRef}
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        aria-busy={isLoading}
        aria-label={`${displayName} conversation messages`}
        className="flex-1 overflow-y-auto bg-gray-50 px-4 py-3 dark:bg-slate-950"
      >
        {isLoading ? (
          <MessageSkeleton rows={5} />
        ) : isError ? (
          <div className="flex h-full items-center justify-center py-8">
            <ErrorState
              title="Messages could not be loaded"
              message="We could not load this conversation right now."
              onRetry={onRetry}
              className="w-full max-w-md"
            />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full items-center justify-center py-8">
            <EmptyState
              icon={<MessageCircle className="h-8 w-8" aria-hidden="true" />}
              title="No messages yet"
              description="Send a message to start this conversation."
              className="w-full max-w-md"
            />
          </div>
        ) : (
          <>
            {/* Messages in chronological order (API returns newest-first, reverse) */}
            {[...messages].reverse().map((msg) => (
              <div key={msg.id} data-msg-id={msg.id} data-highlighted={highlightIds.has(msg.id) ? 'true' : undefined}>
                <ChatMessageBubble
                  message={msg}
                  isOwn={msg.sender_id === user?.id}
                  isRead={
                    msg.sender_id === user?.id && othersLastRead !== null
                      ? new Date(msg.created_at).getTime() <= othersLastRead
                      : undefined
                  }
                  isHighlighted={highlightIds.has(msg.id)}
                  isActiveResult={matchedIds[activeResultIndex] === msg.id}
                />
              </div>
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      <MessageInput onSend={onSend} onFileUpload={onFileUpload} onTyping={onTyping} disabled={!isConnected} />
    </div>
  )
}
