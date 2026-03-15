/**
 * AssistantPage – full-page AI assistant experience with
 * a conversation sidebar and main chat area.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Clock,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import assistantApi from '@/lib/api/assistantApi'
import { useAssistantChat } from '@/features/assistant/useAssistantChat'
import AssistantMessageList from '@/features/assistant/AssistantMessageList'
import AssistantInput from '@/features/assistant/AssistantInput'
import type { AssistantConversation } from '@/types/assistant'

// ── Role-based suggested questions ──────────────────────────────

const ROLE_SUGGESTIONS: Record<string, string[]> = {
  system_admin: [
    'Show me the system health status',
    'List all tenants and their info',
    'Show me all users',
    'What tools can I use?',
  ],
  admin: [
    'Show me all users in my organization',
    'Create a new document',
    'Check our site settings',
    'Help me manage announcements',
  ],
  manager: [
    'List all documents',
    'Show me pending reviews',
    'Search for documents about API',
    'What can I do here?',
  ],
  editor: [
    'Help me create a new document',
    'Search for documents about authentication',
    'Show me my profile info',
    'What tools are available to me?',
  ],
  viewer: [
    'Search for API documentation',
    'Help me find the getting started guide',
    'What documents are available?',
    'Show me my permissions',
  ],
  customer: [
    'Search for API documentation',
    'Help me find the getting started guide',
    "I'd like to submit feedback on a document",
    'How do I create a support ticket?',
  ],
}

// ── Relative-time helper ────────────────────────────────────────

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString()
}

// ── Page component ──────────────────────────────────────────────

export default function AssistantPage() {
  const { user } = useAuth()
  const chat = useAssistantChat()
  const [conversations, setConversations] = useState<AssistantConversation[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [searchFilter, setSearchFilter] = useState('')

  // Load conversations on mount
  useEffect(() => {
    refreshConversations()
    chat.loadTools()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const refreshConversations = async () => {
    try {
      const convs = await assistantApi.getConversations()
      setConversations(convs)
    } catch {
      // silently fail
    }
  }

  const handleNewChat = () => {
    chat.newConversation()
  }

  const handleLoadConversation = useCallback(
    async (id: number) => {
      await chat.loadConversation(id)
    },
    [chat.loadConversation],
  )

  const handleDeleteConversation = useCallback(
    async (id: number) => {
      await chat.deleteConversation(id)
      setConversations(prev => prev.filter(c => c.id !== id))
    },
    [chat.deleteConversation],
  )

  const handleSend = useCallback(
    async (text: string) => {
      await chat.sendMessage(text)
      // Refresh sidebar after first message (new conversation appears)
      setTimeout(refreshConversations, 500)
    },
    [chat.sendMessage],
  )

  const suggestions = ROLE_SUGGESTIONS[user?.role || 'viewer'] || ROLE_SUGGESTIONS.viewer

  const filteredConversations = searchFilter
    ? conversations.filter(c => c.title.toLowerCase().includes(searchFilter.toLowerCase()))
    : conversations

  return (
    <div className="flex h-[calc(100vh-200px)] min-h-[400px] rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* ── Sidebar ──────────────────────────────────────────── */}
      {sidebarOpen && (
        <div className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-slate-50">
          {/* Sidebar header */}
          <div className="flex items-center gap-2 border-b border-slate-200 p-3">
            <button
              type="button"
              onClick={handleNewChat}
              className="flex flex-1 items-center gap-2 rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 transition-colors"
            >
              <MessageSquarePlus className="h-4 w-4" />
              New Chat
            </button>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
              title="Close sidebar"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          </div>

          {/* Search */}
          <div className="px-3 pt-3 pb-1">
            <div className="relative">
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                value={searchFilter}
                onChange={e => setSearchFilter(e.target.value)}
                placeholder="Search chats…"
                className="w-full rounded-lg border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-xs placeholder:text-slate-400 focus:border-sky-400 focus:ring-1 focus:ring-sky-400 outline-none"
              />
            </div>
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
            {filteredConversations.length === 0 && (
              <p className="px-2 py-4 text-center text-xs text-slate-400">
                {searchFilter ? 'No matching conversations' : 'No conversations yet'}
              </p>
            )}
            {filteredConversations.map(conv => (
              <div
                key={conv.id}
                className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm cursor-pointer transition-colors ${
                  conv.id === chat.conversationId
                    ? 'bg-sky-100 text-sky-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
                onClick={() => handleLoadConversation(conv.id)}
              >
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium text-xs">{conv.title}</p>
                  <p className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5">
                    <Clock className="h-3 w-3" />
                    {timeAgo(conv.updated_at)}
                    <span className="ml-1">· {conv.message_count} msg{conv.message_count !== 1 ? 's' : ''}</span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={e => {
                    e.stopPropagation()
                    handleDeleteConversation(conv.id)
                  }}
                  className="hidden group-hover:flex h-6 w-6 items-center justify-center rounded text-slate-400 hover:bg-red-50 hover:text-red-500"
                  title="Delete conversation"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Main chat area ───────────────────────────────────── */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-2.5 bg-slate-50/50">
          {!sidebarOpen && (
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 mr-1"
              title="Open sidebar"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          )}
          <Sparkles className="h-4 w-4 text-sky-600" />
          <h1 className="text-sm font-semibold text-slate-800">AI Assistant</h1>
          <span className="text-xs text-slate-400">
            {chat.availableTools.length > 0 && `${chat.availableTools.length} tools available`}
          </span>
        </div>

        {/* Content – welcome screen or messages */}
        {chat.messages.length === 0 && !chat.isLoading ? (
          <WelcomeScreen
            userName={user?.full_name || 'there'}
            suggestions={suggestions}
            toolCount={chat.availableTools.length}
            onSuggestionClick={handleSend}
          />
        ) : (
          <AssistantMessageList
            messages={chat.messages}
            streamingText={chat.currentStreamText}
            isLoading={chat.isLoading}
            isStreaming={chat.isStreaming}
            activeToolCalls={chat.activeToolCalls}
            toolResults={chat.toolResults}
          />
        )}

        {/* Error */}
        {chat.error && (
          <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
            {chat.error}
          </div>
        )}

        {/* Input */}
        <AssistantInput
          onSend={handleSend}
          onCancel={chat.cancelResponse}
          isLoading={chat.isLoading}
        />
      </div>
    </div>
  )
}

// ── Welcome screen ──────────────────────────────────────────────

function WelcomeScreen({
  userName,
  suggestions,
  toolCount,
  onSuggestionClick,
}: {
  userName: string
  suggestions: string[]
  toolCount: number
  onSuggestionClick: (text: string) => void
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-8">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100">
        <Sparkles className="h-7 w-7 text-sky-600" />
      </div>

      <div className="text-center">
        <h2 className="text-lg font-semibold text-slate-800">
          Hi {userName}! I'm your Portal Assistant.
        </h2>
        <p className="mt-1.5 text-sm text-slate-500 max-w-sm">
          I can help you search documents, manage content, check settings,
          and more. {toolCount > 0 && `I have ${toolCount} tools at your disposal.`}
        </p>
      </div>

      <div className="grid w-full max-w-md gap-2">
        {suggestions.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSuggestionClick(s)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-left text-sm text-slate-600 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
