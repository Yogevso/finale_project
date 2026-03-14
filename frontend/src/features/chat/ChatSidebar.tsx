/**
 * ChatSidebar — list of chats with search, unread badges, last message preview (X1-027)
 */

import { MessageCircle, Search, ArrowRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { ChatListItem, ChatMessage } from '@/types/chat'

/** Strip markdown from a message preview (bold markers, link syntax) */
function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[💬📌]/g, '')
    .replace(/\n/g, ' ')
    .trim()
}

interface ChatSidebarProps {
  chats: ChatListItem[]
  activeChatId: number | null
  searchFilter: string
  onSearchChange: (value: string) => void
  onSelectChat: (chatId: number) => void
  onNewChat: () => void
  globalSearchResults?: ChatMessage[]
  globalSearchLoading?: boolean
  onSelectMessage?: (chatId: number, messageId: number) => void
}

export default function ChatSidebar({
  chats,
  activeChatId,
  searchFilter,
  onSearchChange,
  onSelectChat,
  onNewChat,
  globalSearchResults,
  globalSearchLoading,
  onSelectMessage,
}: ChatSidebarProps) {
  const showGlobalResults = searchFilter.length >= 2 && (globalSearchResults || globalSearchLoading)

  return (
    <div className="flex h-full flex-col border-r border-gray-200 bg-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h2 className="text-lg font-semibold text-gray-900">Messages</h2>
        <button
          onClick={onNewChat}
          className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New
        </button>
      </div>

      {/* Search */}
      <div className="px-4 py-2">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search chats & messages..."
            value={searchFilter}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto">
        {/* Chat name matches */}
        {chats.length === 0 && !showGlobalResults ? (
          <div className="flex flex-col items-center justify-center px-4 py-12 text-gray-400">
            <MessageCircle className="mb-2 h-8 w-8" />
            <p className="text-sm font-medium">No conversations yet</p>
            <p className="mt-0.5 text-xs">Start a new chat to get going</p>
          </div>
        ) : (
          <>
            {chats.map((item) => (
              <ChatListEntry
                key={item.chat.id}
                item={item}
                isActive={item.chat.id === activeChatId}
                onClick={() => onSelectChat(item.chat.id)}
              />
            ))}

            {/* Global message search results */}
            {showGlobalResults && (
              <div className="border-t border-gray-200">
                <div className="px-4 py-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Messages matching "{searchFilter}"
                  </span>
                </div>
                {globalSearchLoading ? (
                  <div className="flex items-center justify-center py-6">
                    <div className="h-5 w-5 animate-spin rounded-full border-b-2 border-blue-600" />
                  </div>
                ) : globalSearchResults && globalSearchResults.length > 0 ? (
                  globalSearchResults.map((msg) => (
                    <GlobalSearchResult
                      key={msg.id}
                      message={msg}
                      searchQuery={searchFilter}
                      onClick={() => onSelectMessage?.(msg.chat_id, msg.id)}
                    />
                  ))
                ) : (
                  <p className="px-4 py-4 text-center text-xs text-gray-400">No messages found</p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

/** Highlight matching substring in text */
function highlightMatch(text: string, query: string) {
  if (!query) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 text-gray-900">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

function GlobalSearchResult({
  message,
  searchQuery,
  onClick,
}: {
  message: ChatMessage
  searchQuery: string
  onClick: () => void
}) {
  const timeAgo = formatDistanceToNow(new Date(message.created_at), { addSuffix: true })
  const snippet = message.content.length > 80
    ? message.content.slice(0, 80) + '…'
    : message.content

  return (
    <button
      onClick={onClick}
      className="w-full px-4 py-2.5 text-left transition-colors hover:bg-blue-50 border-l-3 border-transparent"
    >
      <div className="flex items-start gap-3">
        <div
          className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white ${avatarColor(message.sender_full_name || '?')}`}
        >
          {(message.sender_full_name || '?').charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <span className="truncate text-xs font-medium text-gray-700">
              {message.sender_full_name ?? 'Unknown'}
            </span>
            <span className="ml-2 flex-shrink-0 text-[10px] text-gray-400">{timeAgo}</span>
          </div>
          <p className="mt-0.5 text-xs text-gray-600 line-clamp-2">
            {highlightMatch(snippet, searchQuery)}
          </p>
        </div>
        <ArrowRight className="mt-1 h-3.5 w-3.5 flex-shrink-0 text-gray-300" />
      </div>
    </button>
  )
}

/** Color palette for avatar backgrounds based on first character */
const AVATAR_COLORS = [
  'bg-blue-500',
  'bg-emerald-500',
  'bg-purple-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-cyan-500',
  'bg-indigo-500',
  'bg-pink-500',
]

function avatarColor(name: string) {
  const idx = name.charCodeAt(0) % AVATAR_COLORS.length
  return AVATAR_COLORS[idx]
}

function ChatListEntry({
  item,
  isActive,
  onClick,
}: {
  item: ChatListItem
  isActive: boolean
  onClick: () => void
}) {
  const timeAgo = item.chat.last_message_at
    ? formatDistanceToNow(new Date(item.chat.last_message_at), { addSuffix: true })
    : ''

  const preview = item.last_message
    ? item.last_message.message_type === 'file'
      ? `📎 ${item.last_message.file_name || 'File'}`
      : stripMarkdown(item.last_message.content)
    : ''

  return (
    <button
      onClick={onClick}
      className={`w-full px-4 py-3 text-left transition-colors hover:bg-gray-50 ${
        isActive ? 'bg-blue-50 border-l-3 border-blue-600' : 'border-l-3 border-transparent'
      }`}
    >
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white ${avatarColor(item.display_name)}`}
        >
          {item.display_name.charAt(0).toUpperCase()}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <span className={`truncate text-sm ${item.unread_count > 0 ? 'font-bold text-gray-900' : 'font-medium text-gray-900'}`}>
              {item.display_name}
            </span>
            {timeAgo && (
              <span className={`ml-2 flex-shrink-0 text-[11px] ${item.unread_count > 0 ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>
                {timeAgo}
              </span>
            )}
          </div>
          <div className="mt-0.5 flex items-center justify-between">
            {preview ? (
              <p className={`truncate text-xs ${item.unread_count > 0 ? 'text-gray-700 font-medium' : 'text-gray-500'}`}>
                {preview}
              </p>
            ) : (
              <p className="text-xs text-gray-400 italic">No messages</p>
            )}
            {item.unread_count > 0 && (
              <span className="ml-2 flex h-5 min-w-[1.25rem] flex-shrink-0 items-center justify-center rounded-full bg-blue-600 px-1.5 text-[10px] font-bold text-white">
                {item.unread_count > 99 ? '99+' : item.unread_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}
