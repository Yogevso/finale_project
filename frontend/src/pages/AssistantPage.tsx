/**
 * AssistantPage – full-page AI assistant experience with
 * a conversation sidebar and main chat area.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Clock,
  Download,
  Edit2,
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

// ── Date-group helper ───────────────────────────────────────────

function getDateGroup(dateStr: string): string {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / 86_400_000)

  if (diffDays === 0 && now.getDate() === date.getDate()) return 'Today'
  if (diffDays <= 1 && now.getDate() - date.getDate() === 1) return 'Yesterday'
  if (diffDays < 7) return 'This Week'
  if (diffDays < 30) return 'This Month'
  return 'Older'
}

function groupConversations(convs: AssistantConversation[]): { label: string; items: AssistantConversation[] }[] {
  const groups = new Map<string, AssistantConversation[]>()
  const order = ['Today', 'Yesterday', 'This Week', 'This Month', 'Older']
  for (const c of convs) {
    const label = getDateGroup(c.updated_at)
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label)!.push(c)
  }
  return order.filter(l => groups.has(l)).map(l => ({ label: l, items: groups.get(l)! }))
}

// ── Page component ──────────────────────────────────────────────

export default function AssistantPage() {
  const { user } = useAuth()
  const chat = useAssistantChat()
  const [conversations, setConversations] = useState<AssistantConversation[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [searchFilter, setSearchFilter] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  // Load conversations on mount
  useEffect(() => {
    refreshConversations()
    chat.loadTools()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Refresh sidebar when LLM generates a conversation title
  useEffect(() => {
    if (chat.titleVersion > 0) refreshConversations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat.titleVersion])

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
      setDeleteConfirmId(null)
    },
    [chat.deleteConversation],
  )

  const handleRenameConversation = useCallback(
    async (id: number, newTitle: string) => {
      const trimmed = newTitle.trim()
      if (!trimmed) { setEditingId(null); return }
      try {
        await assistantApi.renameConversation(id, trimmed)
        setConversations(prev =>
          prev.map(c => (c.id === id ? { ...c, title: trimmed } : c)),
        )
      } catch { /* ignore */ }
      setEditingId(null)
    },
    [],
  )

  const handleSend = useCallback(
    async (text: string, documentIds?: number[]) => {
      await chat.sendMessage(text, documentIds)
      // Refresh sidebar after first message (new conversation appears)
      setTimeout(refreshConversations, 500)
    },
    [chat.sendMessage],
  )

  const handleSlashCommand = useCallback(
    (command: string) => {
      switch (command) {
        case '/tools':
          handleSend('What tools are available to me?')
          break
        case '/export':
          chat.exportConversation()
          break
        case '/clear':
          chat.newConversation()
          break
        case '/help':
          handleSend('Show me a guide of keyboard shortcuts and tips for using the assistant')
          break
      }
    },
    [handleSend, chat.exportConversation, chat.newConversation],
  )

  const handleEditMessage = useCallback(
    (index: number, content: string) => {
      const newContent = prompt('Edit message:', content)
      if (newContent !== null && newContent.trim()) {
        chat.editAndResend(index, newContent.trim())
        setTimeout(refreshConversations, 500)
      }
    },
    [chat.editAndResend],
  )

  const suggestions = ROLE_SUGGESTIONS[user?.role || 'viewer'] || ROLE_SUGGESTIONS.viewer

  const filteredConversations = searchFilter
    ? conversations.filter(c => c.title.toLowerCase().includes(searchFilter.toLowerCase()))
    : conversations

  return (
    <div className="flex h-[calc(100vh-200px)] min-h-[400px] rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
      {/* ── Sidebar ──────────────────────────────────────────── */}
      {sidebarOpen && (
        <div className="flex w-60 shrink-0 flex-col border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
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

          {/* Conversation list (grouped by date) */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
            {filteredConversations.length === 0 && (
              <p className="px-2 py-4 text-center text-xs text-slate-400">
                {searchFilter ? 'No matching conversations' : 'No conversations yet'}
              </p>
            )}
            {groupConversations(filteredConversations).map(group => (
              <div key={group.label}>
                <p className="px-2.5 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {group.label}
                </p>
                {group.items.map(conv => (
                  <div
                    key={conv.id}
                    className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm cursor-pointer transition-colors ${
                      conv.id === chat.conversationId
                        ? 'bg-sky-100 text-sky-700'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                    onClick={() => editingId !== conv.id && handleLoadConversation(conv.id)}
                  >
                    <div className="flex-1 min-w-0">
                      {editingId === conv.id ? (
                        <input
                          autoFocus
                          value={editTitle}
                          onChange={e => setEditTitle(e.target.value)}
                          onBlur={() => handleRenameConversation(conv.id, editTitle)}
                          onKeyDown={e => {
                            if (e.key === 'Enter') handleRenameConversation(conv.id, editTitle)
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                          onClick={e => e.stopPropagation()}
                          className="w-full bg-white border border-sky-400 rounded px-1.5 py-0.5 text-xs outline-none focus:ring-1 focus:ring-sky-400"
                        />
                      ) : (
                        <p className="truncate font-medium text-xs">{conv.title}</p>
                      )}
                      <p className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5">
                        <Clock className="h-3 w-3" />
                        {timeAgo(conv.updated_at)}
                        <span className="ml-1">· {conv.message_count} msg{conv.message_count !== 1 ? 's' : ''}</span>
                      </p>
                    </div>
                    <div className="hidden group-hover:flex items-center gap-0.5">
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation()
                          setEditingId(conv.id)
                          setEditTitle(conv.title)
                        }}
                        className="h-6 w-6 flex items-center justify-center rounded text-slate-400 hover:bg-sky-50 hover:text-sky-500"
                        title="Rename conversation"
                      >
                        <Edit2 className="h-3 w-3" />
                      </button>
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation()
                          setDeleteConfirmId(conv.id)
                        }}
                        className="h-6 w-6 flex items-center justify-center rounded text-slate-400 hover:bg-red-50 hover:text-red-500"
                        title="Delete conversation"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Main chat area ───────────────────────────────────── */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-700 px-4 py-2.5 bg-slate-50/50 dark:bg-slate-800/50">
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
          <div className="ml-auto">
            {chat.messages.length > 0 && (
              <button
                type="button"
                onClick={() => chat.exportConversation()}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                title="Export as Markdown"
              >
                <Download className="h-3.5 w-3.5" />
                Export
              </button>
            )}
          </div>
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
            thinkingStatus={chat.thinkingStatus}
            activeToolCalls={chat.activeToolCalls}
            toolResults={chat.toolResults}
            onRegenerate={chat.regenerateLastResponse}
            onEditMessage={handleEditMessage}
          />
        )}

        {/* Error */}
        {chat.error && (
          <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
            {chat.error}
          </div>
        )}

        {/* Follow-up suggestion chips */}
        {chat.suggestions.length > 0 && !chat.isLoading && !chat.isStreaming && (
          <div className="mx-4 mb-2 flex flex-wrap gap-2">
            {chat.suggestions.map((q, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSend(q)}
                className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs text-sky-700 hover:bg-sky-100 hover:border-sky-300 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Confirmation dialog for destructive operations */}
        {chat.confirmRequired && (
          <div className="mx-4 mb-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="text-sm font-medium text-amber-800">
              The AI wants to execute: <span className="font-mono">{chat.confirmRequired.name}</span>
            </p>
            <p className="mt-1 text-xs text-amber-600">
              {JSON.stringify(chat.confirmRequired.arguments)}
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => {
                  chat.dismissConfirm()
                  handleSend(`Yes, please proceed with ${chat.confirmRequired!.name}`)
                }}
                className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 transition-colors"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={() => {
                  chat.dismissConfirm()
                  handleSend(`Cancel the ${chat.confirmRequired!.name} operation`)
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Input */}
        <AssistantInput
          onSend={handleSend}
          onCancel={chat.cancelResponse}
          isLoading={chat.isLoading}
          onSlashCommand={handleSlashCommand}
        />
      </div>

      {/* Delete conversation confirmation modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-slate-800">Delete conversation?</h3>
            <p className="mt-1 text-sm text-slate-500">
              This conversation will be permanently deleted. This action cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleDeleteConversation(deleteConfirmId)}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
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
