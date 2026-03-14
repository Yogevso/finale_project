/**
 * ChatMessage — single message bubble with rich rendering (X1-029)
 */

import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { FileText, ExternalLink, Download, Paperclip, Check, CheckCheck } from 'lucide-react'
import type { ChatMessage as ChatMessageType } from '@/types/chat'

interface ChatMessageProps {
  message: ChatMessageType
  isOwn: boolean
  /** Whether the other participant(s) have read this message */
  isRead?: boolean
  /** Whether this message matches a search query */
  isHighlighted?: boolean
  /** Whether this is the currently focused search result */
  isActiveResult?: boolean
}

// Detect auto-bridged comment messages (start with 💬 Comment on)
const COMMENT_BRIDGE_RE = /^💬 Comment on \*\*(.+?)\*\*\n(?:📌 On: "(.+?)"\n)?\n([\s\S]*?)\n\n\[View in document\]\((.+?)\)$/

/** Parse inline markdown: **bold** and [text](url) → React nodes */
function renderRichText(text: string, isOwn: boolean) {
  const parts: React.ReactNode[] = []
  // Match **bold**, [link text](url), or @document-123 (X1-044)
  const re = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)|@document-(\d+)/g
  let lastIdx = 0
  let match: RegExpExecArray | null
  let key = 0

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index))
    }
    if (match[1]) {
      // Bold
      parts.push(<strong key={key++} className="font-semibold">{match[1]}</strong>)
    } else if (match[2] && match[3]) {
      // Link — internal links start with /
      const href = match[3]
      const isInternal = href.startsWith('/')
      parts.push(
        <a
          key={key++}
          href={href}
          className={`underline ${isOwn ? 'text-blue-200 hover:text-white' : 'text-blue-600 hover:text-blue-800'}`}
          {...(!isInternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
        >
          {match[2]}
        </a>,
      )
    } else if (match[4]) {
      // Document link — @document-123 (X1-044)
      const docId = match[4]
      parts.push(
        <a
          key={key++}
          href={`/documents/${docId}`}
          className={`inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-xs font-medium ${
            isOwn
              ? 'bg-blue-500/30 text-blue-100 hover:bg-blue-500/50'
              : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
          }`}
        >
          📄 Document #{docId}
        </a>,
      )
    }
    lastIdx = re.lastIndex
  }
  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx))
  }
  return parts.length > 0 ? parts : text
}

/** Render an auto-bridged comment as a rich document reference card */
function CommentReferenceCard({
  title,
  anchor,
  content,
  link,
  isOwn,
}: {
  title: string
  anchor: string | null
  content: string
  link: string
  isOwn: boolean
}) {
  const navigate = useNavigate()
  return (
    <div
      className={`rounded-xl overflow-hidden ${
        isOwn ? 'bg-blue-700/50' : 'bg-white border border-gray-200 shadow-sm'
      }`}
    >
      {/* Card header */}
      <div
        className={`flex items-center gap-2 px-3 py-2 ${
          isOwn ? 'bg-blue-700/40 text-blue-100' : 'bg-gray-50 text-gray-600 border-b border-gray-100'
        }`}
      >
        <FileText className="h-4 w-4 flex-shrink-0" />
        <span className="text-xs font-semibold truncate">{title}</span>
      </div>

      {/* Anchor / quoted text */}
      {anchor && (
        <div
          className={`mx-3 mt-2 rounded-lg px-3 py-1.5 text-xs italic ${
            isOwn
              ? 'bg-blue-600/40 text-blue-200 border-l-2 border-blue-300'
              : 'bg-amber-50 text-amber-800 border-l-2 border-amber-400'
          }`}
        >
          "{anchor}"
        </div>
      )}

      {/* Comment content */}
      <div className={`px-3 py-2 text-sm ${isOwn ? 'text-white' : 'text-gray-900'}`}>
        {content}
      </div>

      {/* View link */}
      <div className={`px-3 pb-2`}>
        <button
          onClick={() => navigate(link)}
          className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
            isOwn
              ? 'bg-blue-500/40 text-blue-100 hover:bg-blue-500/60'
              : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
          }`}
        >
          <ExternalLink className="h-3 w-3" />
          View in document
        </button>
      </div>
    </div>
  )
}

export default function ChatMessage({ message, isOwn, isRead, isHighlighted, isActiveResult }: ChatMessageProps) {
  // Check if this is an auto-bridged comment message
  const commentData = useMemo(() => {
    const m = COMMENT_BRIDGE_RE.exec(message.content)
    if (!m) return null
    return { title: m[1], anchor: m[2] || null, content: m[3], link: m[4] }
  }, [message.content])

  if (message.message_type === 'system') {
    return (
      <div className="flex justify-center py-2">
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-500">
          {message.content}
        </span>
      </div>
    )
  }

  const isImage = message.message_type === 'file' && message.file_mime_type?.startsWith('image/')
  const isFile = message.message_type === 'file' && !isImage

  const formatSize = (bytes: number | null) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[75%] ${isOwn ? 'order-2' : ''} ${isActiveResult ? 'ring-2 ring-blue-500 rounded-2xl bg-blue-50/60' : isHighlighted ? 'ring-2 ring-yellow-400 rounded-2xl bg-yellow-50/50' : ''}`}>
        {/* Sender name for received messages */}
        {!isOwn && (
          <p className="mb-0.5 px-1 text-xs font-medium text-gray-500">
            {message.sender_full_name || 'Unknown'}
          </p>
        )}

        {isImage && message.file_url ? (
          /* Image message */
          <div className={`rounded-2xl overflow-hidden ${isOwn ? 'bg-blue-600' : 'bg-gray-100'}`}>
            <a href={message.file_url} target="_blank" rel="noopener noreferrer">
              <img
                src={message.file_url}
                alt={message.file_name || 'image'}
                className="max-h-64 w-auto rounded-2xl object-cover"
                loading="lazy"
              />
            </a>
          </div>
        ) : isFile && message.file_url ? (
          /* File attachment card */
          <div
            className={`flex items-center gap-3 rounded-2xl px-4 py-3 ${
              isOwn ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
            }`}
          >
            <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${isOwn ? 'bg-blue-500' : 'bg-gray-200'}`}>
              <Paperclip className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{message.file_name}</p>
              <p className={`text-xs ${isOwn ? 'text-blue-200' : 'text-gray-400'}`}>{formatSize(message.file_size)}</p>
            </div>
            <a
              href={message.file_url}
              download={message.file_name || undefined}
              className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
                isOwn ? 'hover:bg-blue-500' : 'hover:bg-gray-200'
              }`}
            >
              <Download className="h-4 w-4" />
            </a>
          </div>
        ) : commentData ? (
          /* Rich document reference card for auto-bridged comments */
          <CommentReferenceCard
            title={commentData.title}
            anchor={commentData.anchor}
            content={commentData.content}
            link={commentData.link}
            isOwn={isOwn}
          />
        ) : (
          /* Regular message with inline markdown */
          <div
            className={`rounded-2xl px-4 py-2 ${
              isOwn
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            <p className="whitespace-pre-wrap break-words text-sm">
              {renderRichText(message.content, isOwn)}
            </p>
          </div>
        )}

        <p className={`mt-0.5 px-1 text-[10px] text-gray-400 flex items-center gap-0.5 ${isOwn ? 'justify-end' : ''}`}>
          {message.id < 0 ? (
            <span className="italic">Sending...</span>
          ) : (
            <>
              <span>{formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}</span>
              {isOwn && (
                isRead
                  ? <CheckCheck className="h-3 w-3 text-blue-400" />
                  : <Check className="h-3 w-3" />
              )}
            </>
          )}
        </p>
      </div>
    </div>
  )
}
