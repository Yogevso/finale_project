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
  activeToolCalls: ToolCall[]
  toolResults: Map<string, ToolResult>
  conversationId: number | null
  availableTools: AvailableTool[]
  error: string | null

  sendMessage: (text: string) => Promise<void>
  cancelResponse: () => void
  newConversation: () => void
  loadConversation: (id: number) => Promise<void>
  deleteConversation: (id: number) => Promise<void>
  loadTools: () => Promise<void>
}

export function useAssistantChat(): UseAssistantChat {
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamText, setCurrentStreamText] = useState('')
  const [activeToolCalls, setActiveToolCalls] = useState<ToolCall[]>([])
  const [toolResults, setToolResults] = useState<Map<string, ToolResult>>(new Map())
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([])
  const [error, setError] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  // Accumulates streamed text so the callback closure always has latest value
  const streamAccRef = useRef('')

  // ── Send a message ─────────────────────────────────────────────

  const sendMessage = useCallback(async (text: string) => {
    setError(null)
    setIsLoading(true)
    setIsStreaming(false)
    setCurrentStreamText('')
    setActiveToolCalls([])
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
            case 'conversation_id':
              setConversationId(event.data as number)
              break

            case 'token':
              setIsStreaming(true)
              streamAccRef.current += event.data as string
              setCurrentStreamText(streamAccRef.current)
              break

            case 'tool_call': {
              const tc = event.data as ToolCall
              setActiveToolCalls(prev => [...prev, tc])
              break
            }

            case 'tool_result': {
              const tr = event.data as ToolResult
              setActiveToolCalls(prev => prev.filter(tc => tc.id !== tr.tool_call_id))
              setToolResults(prev => new Map(prev).set(tr.tool_call_id, tr))
              break
            }

            case 'done':
              // Finalize the assistant message
              setMessages(prev => [
                ...prev,
                { role: 'assistant', content: streamAccRef.current || null, created_at: new Date().toISOString() },
              ])
              setCurrentStreamText('')
              setIsStreaming(false)
              streamAccRef.current = ''
              break

            case 'error':
              setError((event.data as { message: string }).message)
              setIsStreaming(false)
              break
          }
        },
        abort.signal,
      )
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
    streamAccRef.current = ''
  }, [])

  // ── New conversation ───────────────────────────────────────────

  const newConversation = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setConversationId(null)
    setCurrentStreamText('')
    setIsStreaming(false)
    setIsLoading(false)
    setActiveToolCalls([])
    setToolResults(new Map())
    setError(null)
    streamAccRef.current = ''
  }, [])

  // ── Load existing conversation ─────────────────────────────────

  const loadConversation = useCallback(async (id: number) => {
    setError(null)
    try {
      const data = await assistantApi.getConversation(id)
      setConversationId(data.id)
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

  return {
    messages,
    isLoading,
    isStreaming,
    currentStreamText,
    activeToolCalls,
    toolResults,
    conversationId,
    availableTools,
    error,
    sendMessage,
    cancelResponse,
    newConversation,
    loadConversation,
    deleteConversation,
    loadTools,
  }
}
