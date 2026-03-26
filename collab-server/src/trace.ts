import { randomUUID } from 'crypto';

import jwt from 'jsonwebtoken';

export const TRACE_ID_HEADER = 'X-Trace-ID';
export const REQUEST_ID_HEADER = 'X-Request-ID';

export function buildTraceHeaders(traceId?: string): Record<string, string> {
  const headers: Record<string, string> = {
    [REQUEST_ID_HEADER]: randomUUID(),
  };
  if (traceId) {
    headers[TRACE_ID_HEADER] = traceId;
  }
  return headers;
}

export function extractTraceIdFromToken(token: string): string | undefined {
  const decoded = jwt.decode(token);
  if (!decoded || typeof decoded !== 'object') {
    return undefined;
  }
  const traceId = (decoded as Record<string, unknown>).trace_id;
  return typeof traceId === 'string' && traceId ? traceId : undefined;
}

export function formatTracePrefix(traceId?: string): string {
  return traceId ? `[trace:${traceId}] ` : '';
}
