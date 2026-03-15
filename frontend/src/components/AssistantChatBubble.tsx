/**
 * AssistantChatBubble – floating chat widget available on every page.
 *
 * States: collapsed (round button), expanded (400×500 panel), minimized (bar).
 * Opens/closes with Ctrl+Shift+A keyboard shortcut.
 * Persists open/closed state in localStorage.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Maximize2,
  MessageSquarePlus,
  Minimize2,
  Sparkles,
  X,
} from 'lucide-react'
import { useAssistantChat } from '@/features/assistant/useAssistantChat'
import AssistantMessageList from '@/features/assistant/AssistantMessageList'
import AssistantInput from '@/features/assistant/AssistantInput'

const LS_KEY = 'assistant-bubble-state'

type BubbleState = 'collapsed' | 'expanded' | 'minimized'

export default function AssistantChatBubble() {
  const [state, setState] = useState<BubbleState>(() => {
    const saved = localStorage.getItem(LS_KEY)
    return saved === 'expanded' || saved === 'minimized' ? saved : 'collapsed'
  })

  const chat = useAssistantChat()

  // Persist state
  useEffect(() => {
    localStorage.setItem(LS_KEY, state)
  }, [state])

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
    (text: string) => {
      chat.sendMessage(text)
    },
    [chat.sendMessage],
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
    <div className="fixed bottom-6 right-6 z-50 flex flex-col w-[400px] h-[500px] max-h-[80vh] max-w-[calc(100vw-48px)] rounded-2xl border border-slate-200 bg-white shadow-2xl animate-in slide-in-from-bottom-4 fade-in duration-200">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-2.5 bg-slate-50 rounded-t-2xl">
        <Sparkles className="h-4 w-4 text-sky-600" />
        <span className="flex-1 text-sm font-semibold text-slate-800">Portal Assistant</span>

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
      <AssistantMessageList
        messages={chat.messages}
        streamingText={chat.currentStreamText}
        isLoading={chat.isLoading}
        isStreaming={chat.isStreaming}
        activeToolCalls={chat.activeToolCalls}
        toolResults={chat.toolResults}
      />

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
  )
}
