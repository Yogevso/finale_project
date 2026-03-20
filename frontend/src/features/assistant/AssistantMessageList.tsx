/**
 * AssistantMessageList – renders the full conversation thread.
 *
 * Handles user messages, assistant messages (with markdown), streaming
 * text, and inline tool-call cards — both live and historical.
 */

import { useEffect, useRef, useState, type CSSProperties } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Bot, Check, Copy, Loader2, Pencil, RefreshCw, User } from 'lucide-react'
import type { AssistantMessage, ToolCall, ToolResult } from '@/types/assistant'
import ToolCallCard from './ToolCallCard'

function timeAgo(dateStr?: string): string {
  if (!dateStr) return ''
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

interface Props {
  messages: AssistantMessage[]
  /** Partial text currently being streamed. */
  streamingText: string
  isLoading: boolean
  isStreaming: boolean
  thinkingStatus: string
  activeToolCalls: ToolCall[]
  toolResults: Map<string, ToolResult>
  onRegenerate?: () => void
  onEditMessage?: (index: number, content: string) => void
}

export default function AssistantMessageList({
  messages,
  streamingText,
  isLoading,
  isStreaming,
  thinkingStatus,
  activeToolCalls,
  toolResults,
  onRegenerate,
  onEditMessage,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, streamingText, activeToolCalls.length])

  // Build a set of tool_call_ids that have corresponding tool messages
  // so we can show completed tool call indicators inline.
  const toolMessageMap = new Map<string, AssistantMessage>()
  for (const msg of messages) {
    if (msg.role === 'tool' && msg.tool_call_id) {
      toolMessageMap.set(msg.tool_call_id, msg)
    }
  }

  return (
    <div
      role="log"
      aria-live="polite"
      aria-relevant="additions text"
      aria-busy={isLoading || isStreaming}
      aria-label="Assistant conversation"
      className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
    >
      {messages.map((msg, i) => {
        // Skip tool messages — they're shown inline with their parent
        if (msg.role === 'tool') return null

        // For assistant messages with tool_calls, render the tool call indicators
        if (msg.role === 'assistant' && msg.tool_calls?.length) {
          return (
            <div
              key={i}
              className="motion-enter-fade space-y-2"
              style={{ '--enter-delay': `${Math.min(i, 6) * 30}ms` } as CSSProperties}
            >
              {msg.content && <MessageBubble message={msg} index={i} onEditMessage={onEditMessage} animationDelayMs={Math.min(i, 6) * 30} />}
              {msg.tool_calls.map(tc => {
                const toolMsg = toolMessageMap.get(tc.id)
                const histResult: ToolResult | undefined = toolMsg
                  ? {
                      tool_call_id: tc.id,
                      name: tc.name,
                      success: true, // if tool message exists, it completed
                      result: toolMsg.content || '',
                      error: null,
                    }
                  : undefined
                return (
                  <ToolCallCard
                    key={tc.id}
                    toolCall={tc}
                    result={histResult}
                  />
                )
              })}
            </div>
          )
        }

        return <MessageBubble key={i} message={msg} index={i} onEditMessage={onEditMessage} animationDelayMs={Math.min(i, 6) * 30} />
      })}

      {/* Active tool calls (executing right now) */}
      {activeToolCalls.map(tc => (
        <ToolCallCard key={tc.id} toolCall={tc} result={toolResults.get(tc.id)} />
      ))}

      {/* Streaming assistant reply — shown whenever there's text to display,
          cursor only pulses while actively receiving tokens */}
      {streamingText && (
        <div className="motion-enter-fade flex items-start gap-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-600">
            <Bot className="h-4 w-4" />
          </div>
          <div className="prose prose-sm max-w-none rounded-xl bg-white p-3 shadow-sm border border-slate-100">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
            {isStreaming && <span className="inline-block h-4 w-1 animate-pulse bg-sky-500 ml-0.5" />}
          </div>
        </div>
      )}

      {/* Thinking indicator — shown during LLM processing and between tool iterations */}
      {isLoading && !isStreaming && (thinkingStatus || activeToolCalls.length === 0) && (
        <div className="motion-enter-fade flex items-start gap-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-600">
            <Bot className="h-4 w-4" />
          </div>
          <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-300">
              <Loader2 className="h-4 w-4 animate-spin text-sky-500" />
              <span>{thinkingStatus || 'Preparing a response…'}</span>
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="h-2 w-2 animate-pulse rounded-full bg-sky-300 [animation-delay:-200ms]" />
              <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400 [animation-delay:-100ms]" />
              <span className="h-2 w-2 animate-pulse rounded-full bg-sky-500" />
            </div>
          </div>
        </div>
      )}

      {/* Regenerate button on last assistant message (only when idle) */}
      {!isLoading && !isStreaming && !streamingText && messages.length > 0 &&
        messages.filter(m => m.role !== 'tool').pop()?.role === 'assistant' && onRegenerate && (
        <div className="motion-enter-fade flex pl-10">
          <button
            onClick={onRegenerate}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors px-2 py-1 rounded hover:bg-slate-100"
          >
            <RefreshCw className="h-3 w-3" />
            Regenerate
          </button>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

// ── Individual message bubble ────────────────────────────────────

function MessageBubble({
  message,
  index,
  onEditMessage,
  animationDelayMs = 0,
}: {
  message: AssistantMessage
  index: number
  onEditMessage?: (index: number, content: string) => void
  animationDelayMs?: number
}) {
  const [copied, setCopied] = useState(false)
  const motionStyle = { '--enter-delay': `${animationDelayMs}ms` } as CSSProperties

  const handleCopyMessage = () => {
    if (!message.content) return
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (message.role === 'user') {
    return (
      <div className="motion-enter-fade group flex items-start justify-end gap-3" style={motionStyle}>
        <div className="flex flex-col items-end">
          <div className="rounded-xl bg-sky-600 text-white px-4 py-2.5 max-w-[80%] shadow-sm">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>
          <div className="flex items-center gap-2 mt-1">
            {onEditMessage && message.content && (
              <button
                type="button"
                onClick={() => onEditMessage(index, message.content || '')}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-slate-600"
                title="Edit & resend"
                aria-label="Edit and resend message"
              >
                <Pencil className="h-3 w-3" />
              </button>
            )}
            {message.created_at && (
              <span className="text-[10px] text-slate-400">{timeAgo(message.created_at)}</span>
            )}
          </div>
        </div>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700">
          <User className="h-4 w-4" />
        </div>
      </div>
    )
  }

  if (message.role === 'assistant' && message.content) {
    return (
      <div className="motion-enter-fade group flex items-start gap-3" style={motionStyle}>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-600">
          <Bot className="h-4 w-4" />
        </div>
        <div className="flex flex-col">
          <div className="prose prose-sm dark:prose-invert max-w-none rounded-xl bg-white dark:bg-slate-800 p-3 shadow-sm border border-slate-100 dark:border-slate-700 max-w-[80%] relative">
            <button
              type="button"
              onClick={handleCopyMessage}
              className={`absolute top-2 right-2 z-10 flex items-center gap-1 rounded-md border border-slate-200 bg-white/90 px-2 py-1 text-xs text-slate-600 opacity-0 transition-opacity hover:bg-slate-100 group-hover:opacity-100 ${copied ? 'motion-enter-scale' : ''}`}
              title="Copy message"
              aria-label={copied ? 'Message copied' : 'Copy message'}
            >
              {copied ? <><Check className="h-3 w-3" /> Copied</> : <><Copy className="h-3 w-3" /> Copy</>}
            </button>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  const codeStr = String(children).replace(/\n$/, '')
                  return match ? (
                    <CodeBlock language={match[1]} code={codeStr} />
                  ) : (
                    <code className={className} {...props}>{children}</code>
                  )
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          {message.created_at && (
            <span className="text-[10px] text-slate-400 mt-1 ml-1">{timeAgo(message.created_at)}</span>
          )}
        </div>
      </div>
    )
  }

  // Tool / system messages are not rendered directly
  return null
}

// ── Code block with copy button ──────────────────────────────────

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <button
        type="button"
        onClick={handleCopy}
        className={`absolute top-2 right-2 z-10 flex items-center gap-1 rounded-md border border-slate-200 bg-white/90 px-2 py-1 text-xs text-slate-600 opacity-0 transition-opacity hover:bg-slate-100 group-hover:opacity-100 ${copied ? 'motion-enter-scale' : ''}`}
        aria-label={copied ? 'Code copied' : 'Copy code block'}
      >
        {copied ? <><Check className="h-3 w-3" /> Copied</> : <><Copy className="h-3 w-3" /> Copy</>}
      </button>
      <SyntaxHighlighter style={oneLight} language={language} PreTag="div">
        {code}
      </SyntaxHighlighter>
    </div>
  )
}
