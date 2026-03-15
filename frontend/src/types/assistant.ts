/** TypeScript types for the AI Assistant feature. */

export interface AssistantConversation {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface AssistantMessage {
  id?: number
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string | null
  tool_calls?: ToolCall[] | null
  tool_call_id?: string | null
  tool_name?: string | null
  created_at?: string
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
}

export interface ToolResult {
  tool_call_id: string
  name: string
  success: boolean
  result: string
  error: string | null
}

export interface AvailableTool {
  name: string
  description: string
  parameters: Record<string, unknown>
}

export interface AssistantHealthStatus {
  status: 'ready' | 'unavailable' | 'disabled'
  model: string
  ollama_healthy: boolean
}

/** SSE event types emitted by the backend /assistant/chat endpoint. */
export type SSEEvent =
  | { event: 'conversation_id'; data: number }
  | { event: 'token'; data: string }
  | { event: 'tool_call'; data: ToolCall }
  | { event: 'tool_result'; data: ToolResult }
  | { event: 'done'; data: { token_count?: number } }
  | { event: 'error'; data: { message: string } }
