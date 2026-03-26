export const COLLAB_SERVER_URL_FALLBACK =
  import.meta.env.VITE_COLLAB_SERVER_URL || 'ws://localhost:8002'
export const MAX_RECONNECT_ATTEMPTS = 10
export const DEFAULT_AUTO_SAVE_INTERVAL = 5 * 60 * 1000
export const COLLAB_TOKEN_REFRESH_INTERVAL_MS = 45 * 60 * 1000
export const COLLAB_ACCESS_RECHECK_INTERVAL_MS = 5 * 60 * 1000
export const COLLAB_ACCESS_REVOKED_MESSAGE =
  'Your collaboration access is no longer valid. Live editing has been disconnected.'

export type CollabServerStatelessMessage =
  | {
      type: 'persistence_failed'
      message: string
    }
  | {
      type: 'persistence_restored'
    }

export function parseCollabServerStatelessMessage(
  payload: string,
): CollabServerStatelessMessage | null {
  try {
    const parsed = JSON.parse(payload)
    if (!parsed || typeof parsed !== 'object' || typeof parsed.type !== 'string') {
      return null
    }

    if (parsed.type === 'persistence_failed' && typeof parsed.message === 'string') {
      return {
        type: 'persistence_failed',
        message: parsed.message,
      }
    }

    if (parsed.type === 'persistence_restored') {
      return {
        type: 'persistence_restored',
      }
    }
  } catch {
    return null
  }

  return null
}

export function getHttpStatusCode(error: unknown): number | null {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof error.response === 'object' &&
    error.response !== null &&
    'status' in error.response &&
    typeof error.response.status === 'number'
  ) {
    return error.response.status
  }

  return null
}

export function resolveCollabServerUrl(
  websocketUrl?: string,
  fallback: string = COLLAB_SERVER_URL_FALLBACK,
): string {
  if (!websocketUrl) {
    return fallback
  }

  const docPathIdx = websocketUrl.lastIndexOf('/document/')
  if (docPathIdx === -1) {
    return websocketUrl
  }

  return websocketUrl.substring(0, docPathIdx)
}
