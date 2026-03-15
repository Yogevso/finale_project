/**
 * useAssistantChat – custom hook managing the AI assistant chat state.
 *
 * Handles message list, SSE streaming, tool-call lifecycle, and
 * conversation CRUD so that UI components stay thin.
 */

import { useCallback, useRef, useState } from 'react'
import assistantApi from '@/lib/api/assistantApi'
import type {
  AssistantMessage,
  AvailableTool,
  SSEEvent,
  ToolCall,
  ToolResult,
} from '@/types/assistant'

export interface UseAssistantChat {
  messages: AssistantMessage[]
  isLoading: boolean
  isStreaming: boolean
  currentStreamText: string
  thinkingStatus: string
  activeToolCalls: ToolCall[]
  toolResults: Map<string, ToolResult>
  conversationId: number | null
  availableTools: AvailableTool[]
  error: string | null
  suggestions: string[]
  confirmRequired: { id: string; name: string; arguments: Record<string, unknown> } | null
  titleVersion: number

  sendMessage: (text: string, documentIds?: number[]) => Promise<void>
  regenerateLastResponse: () => Promise<void>
  cancelResponse: () => void
  newConversation: () => void
  loadConversation: (id: number) => Promise<void>
  deleteConversation: (id: number) => Promise<void>
  loadTools: () => Promise<void>
  dismissConfirm: () => void
  exportConversation: () => void
  editAndResend: (messageIndex: number, newContent: string) => Promise<void>
}

export function useAssistantChat(): UseAssistantChat {
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamText, setCurrentStreamText] = useState('')
  const [thinkingStatus, setThinkingStatus] = useState('')
  const [activeToolCalls, setActiveToolCalls] = useState<ToolCall[]>([])
  const [toolResults, setToolResults] = useState<Map<string, ToolResult>>(new Map())
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([])
  const [error, setError] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [confirmRequired, setConfirmRequired] = useState<{
    id: string; name: string; arguments: Record<string, unknown>
  } | null>(null)
  const [titleVersion, setTitleVersion] = useState(0)

  const abortRef = useRef<AbortController | null>(null)
  // Accumulates streamed text so the callback closure always has latest value
  const streamAccRef = useRef('')
  // Ref to track conversation ID immediately (state updates are async)
  const conversationIdRef = useRef<number | null>(null)

  // ── Send a message ─────────────────────────────────────────────

  const sendMessage = useCallback(async (text: string, documentIds?: number[]) => {
    setError(null)
    setIsLoading(true)
    setIsStreaming(false)
    setCurrentStreamText('')
    setThinkingStatus('')
    setActiveToolCalls([])
    setToolResults(new Map())
    setSuggestions([])
    setConfirmRequired(null)
    streamAccRef.current = ''

    // Append user message immediately
    const userMsg: AssistantMessage = { role: 'user', content: text, created_at: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])

    const abort = new AbortController()
    abortRef.current = abort

    try {
      await assistantApi.sendMessage(
        conversationId,
        text,
        (event: SSEEvent) => {
          switch (event.event) {
            case 'conversation_id': {
              const id = event.data as number
              setConversationId(id)
              conversationIdRef.current = id
              break
            }

            case 'token':
              setIsStreaming(true)
              setThinkingStatus('')
              streamAccRef.current += event.data as string
              setCurrentStreamText(streamAccRef.current)
              break

            case 'thinking': {
              const ts = event.data as { status: string }
              setThinkingStatus(ts.status)
              break
            }

            case 'tool_call': {
              const tc = event.data as ToolCall
              setThinkingStatus('')
              setActiveToolCalls(prev => [...prev, tc])
              break
            }

            case 'tool_result': {
              const tr = event.data as ToolResult
              // Keep the card visible — just mark it as completed via toolResults
              setToolResults(prev => new Map(prev).set(tr.tool_call_id ?? tr.name, tr))
              break
            }

            case 'done':
              // Stop streaming animations — keep text and tool cards
              // visible until the DB reload replaces everything
              setIsStreaming(false)
              setThinkingStatus('')
              break

            case 'suggestions': {
              const s = event.data as { questions: string[] }
              if (s.questions?.length) {
                setSuggestions(s.questions)
              }
              break
            }

            case 'title_updated': {
              setTitleVersion(v => v + 1)
              break
            }

            case 'confirm_required': {
              const cr = event.data as { id: string; name: string; arguments: Record<string, unknown> }
              setConfirmRequired(cr)
              break
            }

            case 'error':
              setError((event.data as { message: string }).message)
              setIsStreaming(false)
              setThinkingStatus('')
              break
          }
        },
        abort.signal,
        documentIds,
      )

      // ── SSE stream completed — reload from DB for perfect rendering ──
      const convId = conversationIdRef.current
      if (convId) {
        try {
          const data = await assistantApi.getConversation(convId)
          // Replace everything atomically (React batches these)
          setMessages(data.messages)
          setActiveToolCalls([])
          setToolResults(new Map())
          setCurrentStreamText('')
          streamAccRef.current = ''
        } catch {
          // Fallback: commit whatever we have as a message
          if (streamAccRef.current) {
            setMessages(prev => [
              ...prev,
              { role: 'assistant', content: streamAccRef.current, created_at: new Date().toISOString() },
            ])
          }
          setActiveToolCalls([])
          setToolResults(new Map())
          setCurrentStreamText('')
          streamAccRef.current = ''
        }
      }
    } catch (err: unknown) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message || 'Something went wrong')
      }
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [conversationId])

  // ── Cancel active stream ───────────────────────────────────────

  const cancelResponse = useCallback(() => {
    abortRef.current?.abort()
    if (streamAccRef.current) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: streamAccRef.current + '\n\n*(cancelled)*', created_at: new Date().toISOString() },
      ])
    }
    setCurrentStreamText('')
    setIsStreaming(false)
    setIsLoading(false)
    setActiveToolCalls([])
    setToolResults(new Map())
    streamAccRef.current = ''
  }, [])

  // ── New conversation ───────────────────────────────────────────

  const newConversation = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setConversationId(null)
    conversationIdRef.current = null
    setCurrentStreamText('')
    setIsStreaming(false)
    setIsLoading(false)
    setActiveToolCalls([])
    setToolResults(new Map())
    setError(null)
    setThinkingStatus('')
    setSuggestions([])
    setConfirmRequired(null)
    streamAccRef.current = ''
  }, [])

  // ── Load existing conversation ─────────────────────────────────

  const loadConversation = useCallback(async (id: number) => {
    setError(null)
    try {
      const data = await assistantApi.getConversation(id)
      setConversationId(data.id)
      conversationIdRef.current = data.id
      setMessages(data.messages)
      setActiveToolCalls([])
      setToolResults(new Map())
      setCurrentStreamText('')
      streamAccRef.current = ''
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to load conversation')
    }
  }, [])

  // ── Delete conversation ────────────────────────────────────────

  const deleteConversation = useCallback(async (id: number) => {
    try {
      await assistantApi.deleteConversation(id)
      if (conversationId === id) {
        newConversation()
      }
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to delete conversation')
    }
  }, [conversationId, newConversation])

  // ── Load available tools ───────────────────────────────────────

  const loadTools = useCallback(async () => {
    try {
      const tools = await assistantApi.getAvailableTools()
      setAvailableTools(tools)
    } catch {
      // non-critical
    }
  }, [])

  // ── Regenerate last response ───────────────────────────────────

  const regenerateLastResponse = useCallback(async () => {
    // Find last user message and strip everything after it
    let lastUserContent = ''
    let sliceIdx = messages.length
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserContent = messages[i].content || ''
        sliceIdx = i  // remove user msg too (sendMessage will re-add it)
        break
      }
    }
    if (!lastUserContent) return
    setMessages(prev => prev.slice(0, sliceIdx))
    await sendMessage(lastUserContent)
  }, [messages, sendMessage])

  const dismissConfirm = useCallback(() => {
    setConfirmRequired(null)
  }, [])

  // ── Export conversation as Markdown ────────────────────────────

  const exportConversation = useCallback(() => {
    if (messages.length === 0) return
    const lines: string[] = ['# Assistant Conversation\n']
    for (const msg of messages) {
      if (msg.role === 'user') {
        lines.push(`## You\n${msg.content}\n`)
      } else if (msg.role === 'assistant' && msg.content) {
        lines.push(`## Assistant\n${msg.content}\n`)
      }
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `conversation-${conversationId || 'new'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [messages, conversationId])

  // ── Edit message and resend from that point ────────────────────

  const editAndResend = useCallback(async (messageIndex: number, newContent: string) => {
    // Slice messages up to the edited message (exclude it + everything after)
    setMessages(prev => prev.slice(0, messageIndex))
    await sendMessage(newContent)
  }, [sendMessage])

  return {
    messages,
    isLoading,
    isStreaming,
    currentStreamText,
    thinkingStatus,
    activeToolCalls,
    toolResults,
    conversationId,
    availableTools,
    error,
    suggestions,
    confirmRequired,
    titleVersion,
    sendMessage,
    regenerateLastResponse,
    cancelResponse,
    newConversation,
    loadConversation,
    deleteConversation,
    loadTools,
    dismissConfirm,
    exportConversation,
    editAndResend,
  }
}
