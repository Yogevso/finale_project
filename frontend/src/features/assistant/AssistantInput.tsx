/**
 * AssistantInput – chat input with send button and keyboard shortcuts.
 *
 * Enter to send, Shift+Enter for newline.
 * Shows a "Stop generating" button when the assistant is actively streaming.
 * Type @ to search and insert document mentions.
 * Type / for slash commands.
 * File upload button with drag-and-drop support.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { FileText, Paperclip, Send, StopCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { API_BASE_URL } from '@/lib/api/httpClient'

interface Props {
  onSend: (text: string, documentIds?: number[], fileIds?: number[]) => void
  onCancel: () => void
  isLoading: boolean
  disabled?: boolean
  onSlashCommand?: (command: string) => void
}

interface DocMention {
  id: number
  title: string
}

export default function AssistantInput({ onSend, onCancel, isLoading, disabled, onSlashCommand }: Props) {
  const [text, setText] = useState('')
  const [mentionSearch, setMentionSearch] = useState<string | null>(null)
  const [mentionResults, setMentionResults] = useState<DocMention[]>([])
  const [mentionIdx, setMentionIdx] = useState(0)
  const [attachedDocs, setAttachedDocs] = useState<DocMention[]>([])
  const [uploadingFile, setUploadingFile] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState<{ id: number; name: string }[]>([])
  const [slashSearch, setSlashSearch] = useState<string | null>(null)
  const [slashIdx, setSlashIdx] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mentionRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const SLASH_COMMANDS = [
    { cmd: '/tools', desc: 'Browse available tools' },
    { cmd: '/export', desc: 'Export conversation as Markdown' },
    { cmd: '/clear', desc: 'Start a new conversation' },
    { cmd: '/help', desc: 'Show keyboard shortcuts & tips' },
  ]

  const filteredSlashCommands = slashSearch !== null
    ? SLASH_COMMANDS.filter(c => c.cmd.startsWith('/' + slashSearch))
    : []

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    // Handle slash commands
    if (trimmed.startsWith('/') && onSlashCommand) {
      const cmd = trimmed.split(' ')[0].toLowerCase()
      if (SLASH_COMMANDS.some(c => c.cmd === cmd)) {
        onSlashCommand(cmd)
        setText('')
        if (textareaRef.current) textareaRef.current.style.height = 'auto'
        return
      }
    }
    const docIds = attachedDocs.map(d => d.id)
    const fileIds = attachedFiles.map(file => file.id)
    onSend(
      trimmed,
      docIds.length > 0 ? docIds : undefined,
      fileIds.length > 0 ? fileIds : undefined,
    )
    setText('')
    setAttachedDocs([])
    setAttachedFiles([])
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  // Click-outside handler for @mention dropdown
  useEffect(() => {
    if (mentionSearch === null) return
    const handler = (e: MouseEvent) => {
      if (mentionRef.current && !mentionRef.current.contains(e.target as Node)) {
        setMentionSearch(null)
        setMentionResults([])
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [mentionSearch])

  // File upload handler
  const handleFileUpload = async (file: File) => {
    setUploadingFile(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      // AD-004: get token from in-memory API client
      const token = api.getToken()
      const res = await fetch(`${API_BASE_URL}/assistant/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      setAttachedFiles(prev => [...prev, { id: data.file_id, name: data.filename }])
    } catch {
      // silently fail
    } finally {
      setUploadingFile(false)
    }
  }

  // Drag-and-drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  // Search documents when mention query changes
  useEffect(() => {
    if (mentionSearch === null) {
      setMentionResults([])
      return
    }
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const result = await api.getDocuments({
          search: mentionSearch || undefined,
          page: 1,
          page_size: 5,
        })
        setMentionResults(
          result.items.map((d: { id: number; title: string }) => ({ id: d.id, title: d.title }))
        )
        setMentionIdx(0)
      } catch {
        setMentionResults([])
      }
    }, 200)
    return () => {
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    }
  }, [mentionSearch])

  const insertMention = useCallback((doc: DocMention) => {
    // Remove the @query from text and insert the document reference
    const atIdx = text.lastIndexOf('@')
    const before = atIdx >= 0 ? text.slice(0, atIdx) : text
    setText(before + `@${doc.title} `)
    setAttachedDocs(prev => {
      if (prev.some(d => d.id === doc.id)) return prev
      return [...prev, doc]
    })
    setMentionSearch(null)
    setMentionResults([])
    textareaRef.current?.focus()
  }, [text])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle mention dropdown navigation
    if (mentionSearch !== null && mentionResults.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setMentionIdx(i => Math.min(i + 1, mentionResults.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setMentionIdx(i => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        insertMention(mentionResults[mentionIdx])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setMentionSearch(null)
        setMentionResults([])
        return
      }
    }

    // Handle slash command navigation
    if (slashSearch !== null && filteredSlashCommands.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSlashIdx(i => Math.min(i + 1, filteredSlashCommands.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSlashIdx(i => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        const cmd = filteredSlashCommands[slashIdx].cmd
        setText(cmd + ' ')
        setSlashSearch(null)
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setSlashSearch(null)
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setText(val)
    // Auto-resize
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`

    // Detect slash command trigger (only at start of input)
    if (val.startsWith('/') && !val.includes(' ') && val.length <= 20) {
      setSlashSearch(val.slice(1))
      setSlashIdx(0)
      setMentionSearch(null)
      return
    }
    setSlashSearch(null)

    // Detect @mention trigger
    const atIdx = val.lastIndexOf('@')
    if (atIdx >= 0) {
      const afterAt = val.slice(atIdx + 1)
      // Only trigger if @ is at start of word and no space before query
      if (!afterAt.includes('\n') && afterAt.length <= 50) {
        setMentionSearch(afterAt)
        return
      }
    }
    setMentionSearch(null)
  }

  return (
    <div
      className={`border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3 ${isDragging ? 'ring-2 ring-blue-400 ring-inset bg-blue-50' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={e => {
          const file = e.target.files?.[0]
          if (file) handleFileUpload(file)
          e.target.value = ''
        }}
      />

      {/* Typing indicator */}
      {isLoading && (
        <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
          AI is typing…
        </div>
      )}

      {/* Attached document badges */}
      {(attachedDocs.length > 0 || attachedFiles.length > 0) && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {attachedDocs.map(doc => (
            <span
              key={`doc-${doc.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-xs text-blue-700"
            >
              <FileText className="h-3 w-3" />
              {doc.title.slice(0, 30)}{doc.title.length > 30 ? '…' : ''}
              <button
                type="button"
                onClick={() => setAttachedDocs(prev => prev.filter(d => d.id !== doc.id))}
                className="ml-0.5 text-blue-400 hover:text-blue-600"
              >
                ×
              </button>
            </span>
          ))}
          {attachedFiles.map(file => (
            <span
              key={`file-${file.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs text-emerald-700"
            >
              <Paperclip className="h-3 w-3" />
              {file.name.slice(0, 30)}{file.name.length > 30 ? '…' : ''}
              <button
                type="button"
                onClick={() => setAttachedFiles(prev => prev.filter(f => f.id !== file.id))}
                className="ml-0.5 text-emerald-400 hover:text-emerald-600"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="relative" ref={mentionRef}>
        {/* Slash command dropdown */}
        {slashSearch !== null && filteredSlashCommands.length > 0 && (
          <div className="absolute bottom-full left-0 mb-1 w-full max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg z-10">
            {filteredSlashCommands.map((cmd, i) => (
              <button
                key={cmd.cmd}
                type="button"
                onClick={() => { setText(cmd.cmd + ' '); setSlashSearch(null) }}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-blue-50 ${
                  i === slashIdx ? 'bg-blue-50 text-blue-700' : 'text-slate-600'
                }`}
              >
                <span className="font-mono text-xs font-medium">{cmd.cmd}</span>
                <span className="text-slate-400 text-xs">{cmd.desc}</span>
              </button>
            ))}
          </div>
        )}

        {/* @mention dropdown */}
        {mentionSearch !== null && mentionResults.length > 0 && (
          <div className="absolute bottom-full left-0 mb-1 w-full max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg z-10">
            {mentionResults.map((doc, i) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => insertMention(doc)}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-blue-50 ${
                  i === mentionIdx ? 'bg-blue-50 text-blue-700' : 'text-slate-600'
                }`}
              >
                <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                <span className="truncate">{doc.title}</span>
                <span className="ml-auto text-[10px] text-slate-400">#{doc.id}</span>
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* File upload button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || uploadingFile}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 transition-colors"
            title="Attach a file"
          >
            {uploadingFile ? (
              <span className="h-4 w-4 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
            ) : (
              <Paperclip className="h-4 w-4" />
            )}
          </button>

          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Type a message… (@ mention docs, attach files, / for commands)"
            rows={1}
            disabled={disabled}
            className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 outline-none disabled:opacity-50 max-h-[200px]"
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
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <p className="mt-1.5 text-[10px] text-slate-400 text-center">
        Enter to send · Shift+Enter for new line · @ to mention a document · attach files for grounding · / for commands
      </p>
    </div>
  )
}
