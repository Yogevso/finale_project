/**
 * AssistantMessageList – renders the full conversation thread.
 *
 * Handles user messages, assistant messages (with markdown), streaming
 * text, and inline tool-call cards.
 */

import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Bot, Loader2, User } from 'lucide-react'
import type { AssistantMessage, ToolCall, ToolResult } from '@/types/assistant'
import ToolCallCard from './ToolCallCard'

interface Props {
  messages: AssistantMessage[]
  /** Partial text currently being streamed. */
  streamingText: string
  isLoading: boolean
  isStreaming: boolean
  activeToolCalls: ToolCall[]
  toolResults: Map<string, ToolResult>
}

export default function AssistantMessageList({
  messages,
  streamingText,
  isLoading,
  isStreaming,
  activeToolCalls,
  toolResults,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, streamingText, activeToolCalls.length])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {/* Active tool calls (executing right now) */}
      {activeToolCalls.map(tc => (
        <ToolCallCard key={tc.id} toolCall={tc} result={toolResults.get(tc.id)} />
      ))}

      {/* Streaming assistant reply */}
      {isStreaming && streamingText && (
        <div className="flex items-start gap-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-600">
            <Bot className="h-4 w-4" />
          </div>
          <div className="prose prose-sm max-w-none rounded-xl bg-white p-3 shadow-sm border border-slate-100">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
            <span className="inline-block h-4 w-1 animate-pulse bg-sky-500 ml-0.5" />
          </div>
        </div>
      )}

      {/* Thinking indicator (before first token) */}
      {isLoading && !isStreaming && activeToolCalls.length === 0 && (
        <div className="flex items-center gap-2 text-slate-400 text-sm pl-10">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Thinking…</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

// ── Individual message bubble ────────────────────────────────────

function MessageBubble({ message }: { message: AssistantMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="rounded-xl bg-sky-600 text-white px-4 py-2.5 max-w-[80%] shadow-sm">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700">
          <User className="h-4 w-4" />
        </div>
      </div>
    )
  }

  if (message.role === 'assistant' && message.content) {
    return (
      <div className="flex items-start gap-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-600">
          <Bot className="h-4 w-4" />
        </div>
        <div className="prose prose-sm max-w-none rounded-xl bg-white p-3 shadow-sm border border-slate-100 max-w-[80%]">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '')
                const codeStr = String(children).replace(/\n$/, '')
                return match ? (
                  <SyntaxHighlighter
                    style={oneLight}
                    language={match[1]}
                    PreTag="div"
                  >
                    {codeStr}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>{children}</code>
                )
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    )
  }

  // Tool / system messages are not rendered directly
  return null
}
