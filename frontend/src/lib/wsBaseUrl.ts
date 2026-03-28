const DEFAULT_BACKEND_WS_PORT = '8000'

export function getDefaultWsBaseUrl(): string {
  if (typeof window === 'undefined') {
    return `ws://localhost:${DEFAULT_BACKEND_WS_PORT}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const hostname = window.location.hostname || 'localhost'
  return `${protocol}://${hostname}:${DEFAULT_BACKEND_WS_PORT}`
}

export const WS_BASE_URL = import.meta.env.VITE_WS_URL || getDefaultWsBaseUrl()
