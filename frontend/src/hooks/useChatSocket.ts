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
  sendMessage: (chatId: number, content: string) => void
  sendTyping: (chatId: number) => void
  markRead: (chatId: number) => void
  joinChat: (chatId: number) => void
}

export function useChatSocket(options: UseChatSocketOptions = {}): UseChatSocketReturn {
  const { enabled = true, onNewMessage, onUserTyping, onMessageRead } = options
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

  const callbacksRef = useRef({ onNewMessage, onUserTyping, onMessageRead })
  callbacksRef.current = { onNewMessage, onUserTyping, onMessageRead }

  const connect = useCallback(() => {
    // AD-004: get token from in-memory API client, not localStorage
    const token = api.getToken()
    if (!token || !enabled) return

    const ws = new WebSocket(`${WS_BASE_URL}/ws/chat?token=${encodeURIComponent(token)}`)

    ws.onopen = () => {
      setIsConnected(true)
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
      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(connect, 3000)
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
    sendMessage: useCallback((chatId: number, content: string) => send('send_message', { chat_id: chatId, content }), [send]),
    sendTyping: useCallback((chatId: number) => send('typing', { chat_id: chatId }), [send]),
    markRead: useCallback((chatId: number) => send('mark_read', { chat_id: chatId }), [send]),
    joinChat: useCallback((chatId: number) => send('join_chat', { chat_id: chatId }), [send]),
  }
}
