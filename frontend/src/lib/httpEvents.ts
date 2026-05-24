export const AUTH_SESSION_EXPIRED_EVENT = 'auth:session-expired'
export const HTTP_RETRYING_EVENT = 'http:retrying'

export interface HttpRetryingEventDetail {
  attempt: number
  maxAttempts: number
  method: string
  url: string
}

function dispatchWindowEvent<T>(eventName: string, detail: T) {
  if (typeof window === 'undefined') {
    return
  }
  window.dispatchEvent(new CustomEvent<T>(eventName, { detail }))
}

export function emitSessionExpired() {
  dispatchWindowEvent(AUTH_SESSION_EXPIRED_EVENT, { at: Date.now() })
}

export function emitHttpRetrying(detail: HttpRetryingEventDetail) {
  dispatchWindowEvent(HTTP_RETRYING_EVENT, detail)
}
