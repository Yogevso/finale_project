import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '@/lib/api'
import type { SupportTicketMessage, SupportWsEvent } from '@/types/chat'

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const RECONNECT_BASE_MS = 3000
const RECONNECT_CAP_MS = 60000

function nextBackoff(attempt: number): number {
  return Math.min(RECONNECT_BASE_MS * Math.pow(2, attempt), RECONNECT_CAP_MS)
}

export interface UseSupportSocketOptions {
  enabled?: boolean
  activeTicketId?: number | null
  onNewMessage?: (message: SupportTicketMessage) => void
  onStatusUpdate?: (data: { ticket_id: number; status: string }) => void
}

export interface UseSupportSocketReturn {
  isConnected: boolean
}

export function useSupportSocket(options: UseSupportSocketOptions = {}): UseSupportSocketReturn {
  const {
    enabled = true,
    activeTicketId = null,
    onNewMessage,
    onStatusUpdate,
  } = options
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const attemptRef = useRef(0)
  const shouldReconnectRef = useRef(enabled)
  const activeTicketIdRef = useRef<number | null>(activeTicketId)
  const callbacksRef = useRef({ onNewMessage, onStatusUpdate })

  callbacksRef.current = { onNewMessage, onStatusUpdate }
  activeTicketIdRef.current = activeTicketId
  shouldReconnectRef.current = enabled

  const joinTicket = useCallback((ticketId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event: 'join_ticket', data: { ticket_id: ticketId } }))
    }
  }, [])

  const connect = useCallback(() => {
    const token = api.getToken()
    if (!token || !enabled) {
      return
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/support`)

    ws.onopen = () => {
      ws.send(JSON.stringify({ event: 'authenticate', data: { token } }))
      setIsConnected(true)
      attemptRef.current = 0

      if (activeTicketIdRef.current) {
        ws.send(JSON.stringify({ event: 'join_ticket', data: { ticket_id: activeTicketIdRef.current } }))
      }
    }

    ws.onmessage = (event) => {
      try {
        const message: SupportWsEvent = JSON.parse(event.data)
        switch (message.event) {
          case 'new_message':
            callbacksRef.current.onNewMessage?.(message.data as unknown as SupportTicketMessage)
            break
          case 'status_update':
            callbacksRef.current.onStatusUpdate?.(
              message.data as unknown as { ticket_id: number; status: string },
            )
            break
        }
      } catch {
        // Ignore malformed websocket payloads.
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      wsRef.current = null

      if (!shouldReconnectRef.current) {
        return
      }

      const delay = nextBackoff(attemptRef.current)
      attemptRef.current += 1
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
      shouldReconnectRef.current = false
      clearTimeout(reconnectTimeoutRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  useEffect(() => {
    if (activeTicketId) {
      joinTicket(activeTicketId)
    }
  }, [activeTicketId, joinTicket])

  return { isConnected }
}
