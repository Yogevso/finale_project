/**
 * MessageInput — multiline input with Enter to send, Shift+Enter for newline,
 * plus file/image upload (X1-032)
 */

import { useState, useRef, useCallback, useEffect, useId } from 'react'
import { Send, Paperclip, Image, X, Smile } from 'lucide-react'
import data from '@emoji-mart/data'
import Picker from '@emoji-mart/react'
import OptimizedImage from '@/components/OptimizedImage'
import { COMMUNICATION_INPUT_LIMITS, normalizeMultilineInput } from '@/lib/uiInputRules'
import {
  PLATFORM_UPLOAD_MAX_SIZE_BYTES,
  PLATFORM_UPLOAD_MAX_SIZE_MB,
} from '@/lib/uploadLimits'

const MAX_FILE_SIZE = PLATFORM_UPLOAD_MAX_SIZE_BYTES

interface MessageInputProps {
  onSend: (content: string) => void
  onFileUpload?: (file: File) => void
  onTyping: () => void
  disabled?: boolean
  placeholder?: string
}

export default function MessageInput({
  onSend,
  onFileUpload,
  onTyping,
  disabled = false,
  placeholder = 'Type a message...',
}: MessageInputProps) {
  const [value, setValue] = useState('')
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const emojiPickerRef = useRef<HTMLDivElement>(null)
  const emojiButtonRef = useRef<HTMLButtonElement>(null)
  const emojiPickerId = useId()

  // Close emoji picker on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (emojiPickerRef.current && !emojiPickerRef.current.contains(e.target as Node)) {
        setShowEmojiPicker(false)
      }
    }
    if (showEmojiPicker) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showEmojiPicker])

  useEffect(() => {
    if (!showEmojiPicker) {
      return
    }

    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowEmojiPicker(false)
        emojiButtonRef.current?.focus()
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [showEmojiPicker])

  const handleEmojiSelect = useCallback((emoji: { native: string }) => {
    setValue((prev) => prev + emoji.native)
    setShowEmojiPicker(false)
    textareaRef.current?.focus()
  }, [])

  const handleSend = useCallback(() => {
    if (pendingFile && onFileUpload) {
      onFileUpload(pendingFile)
      setPendingFile(null)
      setPreviewUrl(null)
      return
    }
    const trimmed = normalizeMultilineInput(value, COMMUNICATION_INPUT_LIMITS.chatMessage)
    if (!trimmed) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value, onSend, pendingFile, onFileUpload])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value)
    onTyping()
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`
  }

  const handleFileSelected = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > MAX_FILE_SIZE) {
      alert(`File is too large (max ${PLATFORM_UPLOAD_MAX_SIZE_MB} MB)`)
      return
    }
    setPendingFile(file)
    if (file.type.startsWith('image/')) {
      setPreviewUrl(URL.createObjectURL(file))
    } else {
      setPreviewUrl(null)
    }
    // Reset input so the same file can be re-selected
    e.target.value = ''
  }, [])

  const clearPending = useCallback(() => {
    setPendingFile(null)
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
  }, [previewUrl])

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="border-t border-gray-200 bg-white">
      {/* File preview */}
      {pendingFile && (
        <div className="flex items-center gap-3 px-4 pt-3">
          {previewUrl ? (
            <OptimizedImage
              src={previewUrl}
              alt="preview"
              className="h-16 w-16 rounded-lg border border-gray-200 object-cover"
              height={64}
              width={64}
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-gray-100 border border-gray-200">
              <Paperclip className="h-6 w-6 text-gray-400" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-700 truncate">{pendingFile.name}</p>
            <p className="text-xs text-gray-400">{formatSize(pendingFile.size)}</p>
          </div>
          <button
            type="button"
            onClick={clearPending}
            className="p-1 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600"
            aria-label={`Remove ${pendingFile.name}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="flex items-end gap-2 px-4 py-3">
        {/* Hidden file inputs */}
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileSelected} />
        <input ref={imageInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileSelected} />

        {/* Attachment button */}
        {onFileUpload && (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-50"
            title="Attach file"
            aria-label="Attach file"
          >
            <Paperclip className="h-4 w-4" />
          </button>
        )}

        {/* Image button */}
        {onFileUpload && (
          <button
            type="button"
            onClick={() => imageInputRef.current?.click()}
            disabled={disabled}
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-50"
            title="Send image"
            aria-label="Send image"
          >
            <Image className="h-4 w-4" />
          </button>
        )}

        {/* Emoji picker */}
        <div className="relative" ref={emojiPickerRef}>
          <button
            ref={emojiButtonRef}
            type="button"
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            disabled={disabled}
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-50"
            title="Emoji"
            aria-label={showEmojiPicker ? 'Close emoji picker' : 'Open emoji picker'}
            aria-expanded={showEmojiPicker}
            aria-haspopup="dialog"
            aria-controls={emojiPickerId}
          >
            <Smile className="h-4 w-4" />
          </button>
          {showEmojiPicker && (
            <div
              id={emojiPickerId}
              role="dialog"
              aria-label="Emoji picker"
              className="absolute bottom-12 left-0 z-50"
            >
              <Picker data={data} onEmojiSelect={handleEmojiSelect} theme="light" previewPosition="none" skinTonePosition="none" maxFrequentRows={1} />
            </div>
          )}
        </div>

        <textarea
          ref={textareaRef}
          value={pendingFile ? '' : value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={pendingFile ? `Send ${pendingFile.name}` : placeholder}
          disabled={disabled || !!pendingFile}
          rows={1}
          maxLength={COMMUNICATION_INPUT_LIMITS.chatMessage}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={disabled || (!value.trim() && !pendingFile)}
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-sky-600 text-white transition-colors hover:bg-sky-700 disabled:opacity-50"
          aria-label={pendingFile ? `Send ${pendingFile.name}` : 'Send message'}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      {!pendingFile ? (
        <div className="px-4 pb-3 text-right text-xs text-gray-400">
          {value.length}/{COMMUNICATION_INPUT_LIMITS.chatMessage}
        </div>
      ) : null}
    </div>
  )
}
