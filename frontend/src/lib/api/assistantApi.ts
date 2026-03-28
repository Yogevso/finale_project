/**
 * Assistant API client with SSE stream support.
 *
 * Uses raw fetch() for the streaming /chat endpoint and the shared
 * Axios httpClient for regular REST calls.
 */

import type {
  AssistantConversation,
  AssistantHealthStatus,
  AssistantMessage,
  AvailableTool,
  SSEEvent,
} from '@/types/assistant'
import { API_BASE_URL } from './httpClient'
import { api } from '@/lib/api'
import { withTraceHeader } from '@/lib/requestTrace'

// ── Helpers ──────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  // AD-004: get token from in-memory API client, not localStorage
  const token = api.getToken()
  const headers: Record<string, string> = withTraceHeader({ 'Content-Type': 'application/json' })
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

/**
 * Parse an SSE text/event-stream.
 * Handles partial chunks and multi-event batches.
 */
async function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Split on double newline (SSE event separator)
    const parts = buffer.split('\n\n')
    // Last part may be incomplete — keep in buffer
    buffer = parts.pop() || ''

    for (const part of parts) {
      if (!part.trim()) continue
      // Skip SSE comments (keepalive heartbeats)
      if (part.trim().startsWith(':')) continue

      let eventName = 'message'
      let eventData = ''

      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) {
          eventName = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          eventData = line.slice(6)
        }
      }

      if (!eventName) continue

      try {
        let parsed: unknown = eventData

        // Attempt JSON parse for structured events
        if (eventName !== 'token') {
          try {
            parsed = JSON.parse(eventData)
          } catch {
            // keep as string
          }
        }

        onEvent({ event: eventName, data: parsed } as SSEEvent)
      } catch {
        // skip malformed events
      }
    }
  }
}

// ── Public API ───────────────────────────────────────────────────

const assistantApi = {
  /**
   * Send a user message and stream the assistant response via SSE.
   */
  async sendMessage(
    conversationId: number | null,
    message: string,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal,
    documentIds?: number[],
    fileIds?: number[],
  ): Promise<void> {
    const body: Record<string, unknown> = { conversation_id: conversationId, message }
    if (documentIds && documentIds.length > 0) body.document_ids = documentIds
    if (fileIds && fileIds.length > 0) body.file_ids = fileIds
    const res = await fetch(`${API_BASE_URL}/assistant/chat`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal,
    })

    if (!res.ok) {
      const text = await res.text()
      let detail = 'Failed to send message'
      try { detail = JSON.parse(text).detail || detail } catch { /* use default */ }
      throw new Error(detail)
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('No response body')

    await parseSSEStream(reader, onEvent)
  },

  /**
   * List the current user's conversations.
   */
  async getConversations(limit = 50): Promise<AssistantConversation[]> {
    const res = await fetch(`${API_BASE_URL}/assistant/conversations?limit=${limit}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Failed to load conversations')
    return res.json()
  },

  /**
   * Create a new empty conversation.
   */
  async createConversation(title = 'New Chat'): Promise<AssistantConversation> {
    const res = await fetch(
      `${API_BASE_URL}/assistant/conversations?title=${encodeURIComponent(title)}`,
      { method: 'POST', headers: authHeaders() },
    )
    if (!res.ok) throw new Error('Failed to create conversation')
    return res.json()
  },

  /**
   * Get a conversation with all messages.
   */
  async getConversation(id: number): Promise<{ id: number; title: string; messages: AssistantMessage[]; created_at: string }> {
    const res = await fetch(`${API_BASE_URL}/assistant/conversations/${id}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Conversation not found')
    return res.json()
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(id: number): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/assistant/conversations/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Failed to delete conversation')
  },

  /**
   * Rename a conversation.
   */
  async renameConversation(id: number, title: string): Promise<void> {
    const res = await fetch(
      `${API_BASE_URL}/assistant/conversations/${id}?title=${encodeURIComponent(title)}`,
      { method: 'PATCH', headers: authHeaders() },
    )
    if (!res.ok) throw new Error('Failed to rename conversation')
  },

  /**
   * List tools available to the current user.
   */
  async getAvailableTools(): Promise<AvailableTool[]> {
    const res = await fetch(`${API_BASE_URL}/assistant/tools`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Failed to load tools')
    return res.json()
  },

  /**
   * Check Ollama health / readiness.
   */
  async getHealth(): Promise<AssistantHealthStatus> {
    const res = await fetch(`${API_BASE_URL}/assistant/health`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Health check failed')
    return res.json()
  },
}

export default assistantApi
