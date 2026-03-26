export const TRACE_ID_HEADER = 'X-Trace-ID'

function fallbackTraceId(): string {
  return `trace-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export function generateTraceId(): string {
  if (typeof globalThis !== 'undefined' && globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID()
  }
  return fallbackTraceId()
}

export function withTraceHeader(
  headers: Record<string, string> = {},
  traceId: string = generateTraceId(),
): Record<string, string> {
  if (headers[TRACE_ID_HEADER]) {
    return headers
  }
  return {
    ...headers,
    [TRACE_ID_HEADER]: traceId,
  }
}
