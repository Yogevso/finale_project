/**
 * useChatSocket — WebSocket hook for real-time chat (Wave X.1)
 *
 * Manages connection lifecycle, message receiving, typing indicators, and read receipts.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage, ChatWsEvent } from '@/types/chat'
import { api } from '@/lib/api'

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export interface UseChatSocketOptions {
  enabled?: boolean
  onNewMessage?: (message: ChatMessage) => void
  onUserTyping?: (data: { chat_id: number; user_id: number; username: string }) => void
  onMessageRead?: (data: { chat_id: number; user_id: number }) => void
}

export interface UseChatSocketReturn {
  isConnected: boolean
  connectionFailures: number
  sendMessage: (chatId: number, content: string) => void
  sendTyping: (chatId: number) => void
  markRead: (chatId: number) => void
  joinChat: (chatId: number) => void
}

// Exponential backoff: 3s → 6s → 12s → 30s → cap 60s
const RECONNECT_BASE_MS = 3000
const RECONNECT_CAP_MS = 60000

function nextBackoff(attempt: number): number {
  return Math.min(RECONNECT_BASE_MS * Math.pow(2, attempt), RECONNECT_CAP_MS)
}

export function useChatSocket(options: UseChatSocketOptions = {}): UseChatSocketReturn {
  const { enabled = true, onNewMessage, onUserTyping, onMessageRead } = options
  const [isConnected, setIsConnected] = useState(false)
  const [connectionFailures, setConnectionFailures] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const attemptRef = useRef(0)

  const callbacksRef = useRef({ onNewMessage, onUserTyping, onMessageRead })
  callbacksRef.current = { onNewMessage, onUserTyping, onMessageRead }

  const connect = useCallback(() => {
    // AD-004: get token from in-memory API client, not localStorage
    const token = api.getToken()
    if (!token || !enabled) return

    const ws = new WebSocket(`${WS_BASE_URL}/ws/chat?token=${encodeURIComponent(token)}`)

    ws.onopen = () => {
      setIsConnected(true)
      attemptRef.current = 0
      setConnectionFailures(0)
    }

    ws.onmessage = (event) => {
      try {
        const msg: ChatWsEvent = JSON.parse(event.data)
        switch (msg.event) {
          case 'new_message':
            callbacksRef.current.onNewMessage?.(msg.data as unknown as ChatMessage)
            break
          case 'user_typing':
            callbacksRef.current.onUserTyping?.(
              msg.data as unknown as { chat_id: number; user_id: number; username: string },
            )
            break
          case 'message_read':
            callbacksRef.current.onMessageRead?.(
              msg.data as unknown as { chat_id: number; user_id: number },
            )
            break
        }
      } catch {
        // ignore malformed
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      wsRef.current = null
      // Exponential backoff reconnection
      const delay = nextBackoff(attemptRef.current)
      attemptRef.current += 1
      setConnectionFailures(attemptRef.current)
      reconnectTimeoutRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [enabled])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeoutRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((event: string, data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event, data }))
    }
  }, [])

  return {
    isConnected,
    connectionFailures,
    sendMessage: useCallback((chatId: number, content: string) => send('send_message', { chat_id: chatId, content }), [send]),
    sendTyping: useCallback((chatId: number) => send('typing', { chat_id: chatId }), [send]),
    markRead: useCallback((chatId: number) => send('mark_read', { chat_id: chatId }), [send]),
    joinChat: useCallback((chatId: number) => send('join_chat', { chat_id: chatId }), [send]),
  }
}
