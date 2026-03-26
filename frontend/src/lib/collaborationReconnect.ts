const DEFAULT_BASE_RECONNECT_DELAY_MS = 1000
const DEFAULT_MAX_RECONNECT_DELAY_MS = 30000
const MIN_JITTER_FACTOR = 0.8
const JITTER_RANGE = 0.4

export function getReconnectDelay(
  attempt: number,
  randomValue: number = Math.random(),
  baseDelayMs: number = DEFAULT_BASE_RECONNECT_DELAY_MS,
  maxDelayMs: number = DEFAULT_MAX_RECONNECT_DELAY_MS,
): number {
  const normalizedAttempt = Math.max(attempt, 1)
  const cappedBackoff = Math.min(baseDelayMs * Math.pow(2, normalizedAttempt - 1), maxDelayMs)
  const jitterFactor = MIN_JITTER_FACTOR + Math.min(Math.max(randomValue, 0), 1) * JITTER_RANGE
  return Math.min(Math.round(cappedBackoff * jitterFactor), maxDelayMs)
}
