/**
 * AssistantInput – chat input with send button and keyboard shortcuts.
 *
 * Enter to send, Shift+Enter for newline.
 * Shows a "Stop generating" button when the assistant is actively streaming.
 */

import { useRef, useState } from 'react'
import { Send, StopCircle } from 'lucide-react'

interface Props {
  onSend: (text: string) => void
  onCancel: () => void
  isLoading: boolean
  disabled?: boolean
}

export default function AssistantInput({ onSend, onCancel, isLoading, disabled }: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setText('')
    // Reset textarea height
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    // Auto-resize
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  return (
    <div className="border-t border-slate-200 bg-white px-4 py-3">
      {/* Typing indicator */}
      {isLoading && (
        <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
          AI is typing…
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Type a message…"
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm placeholder:text-slate-400 focus:border-sky-400 focus:ring-1 focus:ring-sky-400 outline-none disabled:opacity-50 max-h-[200px]"
        />

        {isLoading ? (
          <button
            type="button"
            onClick={onCancel}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-500 hover:bg-red-100 transition-colors"
            title="Stop generating"
          >
            <StopCircle className="h-5 w-5" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>

      <p className="mt-1.5 text-[10px] text-slate-400 text-center">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
