/**
 * AssistantChatBubble – floating chat widget available on every page.
 *
 * States: collapsed (round button), expanded (400×500 panel), minimized (bar).
 * Opens/closes with Ctrl+Shift+A keyboard shortcut.
 * Persists open/closed state in localStorage.
 */

import { Suspense, lazy, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Clock,
  History,
  Maximize2,
  MessageSquarePlus,
  Minimize2,
  Sparkles,
  X,
} from 'lucide-react'
import assistantApi from '@/lib/api/assistantApi'
import { useAssistantChat } from '@/features/assistant/useAssistantChat'
import AssistantMessageListFallback from '@/features/assistant/AssistantMessageListFallback'
import AssistantInput from '@/features/assistant/AssistantInput'
import type { AssistantConversation } from '@/types/assistant'

const LS_KEY = 'assistant-bubble-state'
const AssistantMessageList = lazy(() => import('@/features/assistant/AssistantMessageList'))

type BubbleState = 'collapsed' | 'expanded' | 'minimized'

export default function AssistantChatBubble() {
  const [state, setState] = useState<BubbleState>(() => {
    const saved = localStorage.getItem(LS_KEY)
    return saved === 'expanded' || saved === 'minimized' ? saved : 'collapsed'
  })

  const chat = useAssistantChat()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [recentConversations, setRecentConversations] = useState<AssistantConversation[]>([])

  // Persist state
  useEffect(() => {
    localStorage.setItem(LS_KEY, state)
  }, [state])

  // Load recent conversations when history dropdown opens
  useEffect(() => {
    if (historyOpen) {
      assistantApi.getConversations(10).then(setRecentConversations).catch(() => {})
    }
  }, [historyOpen])

  // Keyboard shortcut: Ctrl+Shift+A
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        e.preventDefault()
        setState(prev => (prev === 'collapsed' ? 'expanded' : 'collapsed'))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleSend = useCallback(
    (text: string, documentIds?: number[]) => {
      chat.sendMessage(text, documentIds)
    },
    [chat],
  )

  // ── Collapsed: floating button ────────────────────────────────

  if (state === 'collapsed') {
    return (
      <button
        type="button"
        onClick={() => setState('expanded')}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-sky-600 text-white shadow-lg transition-transform hover:scale-110 hover:bg-sky-700"
        title="Open AI Assistant (Ctrl+Shift+A)"
      >
        <Sparkles className="h-5 w-5" />
      </button>
    )
  }

  // ── Minimized: slim bar ───────────────────────────────────────

  if (state === 'minimized') {
    return (
      <button
        type="button"
        onClick={() => setState('expanded')}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-sky-600 pl-4 pr-3 py-2 text-white shadow-lg hover:bg-sky-700 transition-colors text-sm"
      >
        <Sparkles className="h-4 w-4" />
        <span className="max-w-[180px] truncate">Portal Assistant</span>
        <Maximize2 className="h-3.5 w-3.5 opacity-70" />
      </button>
    )
  }

  // ── Expanded: chat panel ──────────────────────────────────────

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col w-[400px] h-[500px] max-h-[80vh] max-w-[calc(100vw-48px)] rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-2xl animate-in slide-in-from-bottom-4 fade-in duration-200">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-700 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 rounded-t-2xl">
        <Sparkles className="h-4 w-4 text-sky-600" />
        <span className="flex-1 text-sm font-semibold text-slate-800">Portal Assistant</span>

        {/* History */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setHistoryOpen(!historyOpen)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            title="Recent conversations"
          >
            <History className="h-4 w-4" />
          </button>
          {historyOpen && (
            <div className="absolute right-0 top-9 z-50 w-56 rounded-lg border border-slate-200 bg-white shadow-lg py-1 max-h-64 overflow-y-auto">
              {recentConversations.length === 0 ? (
                <p className="px-3 py-2 text-xs text-slate-400">No conversations yet</p>
              ) : (
                recentConversations.map(c => (
                  <button
                    key={c.id}
                    type="button"
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 ${
                      c.id === chat.conversationId ? 'bg-sky-50 text-sky-700' : 'text-slate-600'
                    }`}
                    onClick={() => {
                      chat.loadConversation(c.id)
                      setHistoryOpen(false)
                    }}
                  >
                    <p className="truncate font-medium">{c.title}</p>
                    <p className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5">
                      <Clock className="h-2.5 w-2.5" />
                      {c.message_count} messages
                    </p>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* New Chat */}
        <button
          type="button"
          onClick={chat.newConversation}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          title="New conversation"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </button>

        {/* Open full page */}
        <Link
          to="/assistant"
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          title="Open full page"
        >
          <Maximize2 className="h-4 w-4" />
        </Link>

        {/* Minimize */}
        <button
          type="button"
          onClick={() => setState('minimized')}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          title="Minimize"
        >
          <Minimize2 className="h-4 w-4" />
        </button>

        {/* Close */}
        <button
          type="button"
          onClick={() => setState('collapsed')}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-red-500"
          title="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <Suspense fallback={<AssistantMessageListFallback className="min-h-0" />}>
        <AssistantMessageList
          messages={chat.messages}
          streamingText={chat.currentStreamText}
          isLoading={chat.isLoading}
          isStreaming={chat.isStreaming}
          thinkingStatus={chat.thinkingStatus}
          activeToolCalls={chat.activeToolCalls}
          toolResults={chat.toolResults}
          onRegenerate={chat.regenerateLastResponse}
          onEditMessage={(idx, content) => chat.editAndResend(idx, content)}
        />
      </Suspense>

      {/* Error */}
      {chat.error && (
        <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
          {chat.error}
        </div>
      )}

      {/* Follow-up suggestion chips */}
      {chat.suggestions.length > 0 && !chat.isLoading && !chat.isStreaming && (
        <div className="mx-3 mb-2 flex flex-wrap gap-1.5">
          {chat.suggestions.map((q, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSend(q)}
              className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] text-sky-700 hover:bg-sky-100 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Confirmation dialog for destructive operations */}
      {chat.confirmRequired && (
        <div className="mx-3 mb-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs font-medium text-amber-800">
            Execute: <span className="font-mono">{chat.confirmRequired.name}</span>
          </p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => {
                chat.dismissConfirm()
                handleSend(`Yes, please proceed with ${chat.confirmRequired!.name}`)
              }}
              className="rounded-lg bg-amber-600 px-3 py-1 text-xs font-medium text-white hover:bg-amber-700 transition-colors"
            >
              Confirm
            </button>
            <button
              type="button"
              onClick={() => {
                chat.dismissConfirm()
                handleSend(`Cancel the ${chat.confirmRequired!.name} operation`)
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
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
      />
    </div>
  )
}
