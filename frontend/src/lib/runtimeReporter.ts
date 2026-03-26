import { toast } from 'sonner'

export type RuntimeReportLevel = 'error' | 'warn'

export interface RuntimeReporterEvent {
  level: RuntimeReportLevel
  scope: string
  message: string
  userMessage: string | null
  error: unknown
}

interface RuntimeReportOptions {
  scope: string
  message: string
  error?: unknown
  userMessage?: string
  toastTitle?: string
  dedupeKey?: string
  dedupeMs?: number
  reporterMetadata?: unknown
}

type RuntimeReportingWindow = Window & {
  __ERROR_REPORTER__?: (error: Error, metadata?: unknown) => void
  __RUNTIME_REPORTER__?: (event: RuntimeReporterEvent) => void
}

const notificationTimestamps = new Map<string, number>()
const DEFAULT_DEDUPE_MS = 60_000

function normalizeError(error: unknown, fallbackMessage: string): Error {
  if (error instanceof Error) {
    return error
  }

  if (typeof error === 'string' && error.trim()) {
    return new Error(error)
  }

  return new Error(fallbackMessage)
}

function getRuntimeWindow(): RuntimeReportingWindow | null {
  if (typeof window === 'undefined') {
    return null
  }

  return window as RuntimeReportingWindow
}

function shouldNotify(key: string, dedupeMs: number): boolean {
  const now = Date.now()
  const lastTimestamp = notificationTimestamps.get(key)
  if (lastTimestamp !== undefined && now - lastTimestamp < dedupeMs) {
    return false
  }

  notificationTimestamps.set(key, now)
  return true
}

function emitRuntimeReport(level: RuntimeReportLevel, options: RuntimeReportOptions): void {
  const { scope, message, error, userMessage, toastTitle } = options
  const dedupeMs = options.dedupeMs ?? DEFAULT_DEDUPE_MS
  const dedupeKey = options.dedupeKey ?? `${level}:${scope}:${message}:${userMessage ?? ''}`
  const prefix = `[${scope}] ${message}`
  const runtimeWindow = getRuntimeWindow()
  const payload: RuntimeReporterEvent = {
    level,
    scope,
    message,
    userMessage: userMessage ?? null,
    error: error ?? null,
  }

  if (level === 'error') {
    console.error(prefix, error)
    runtimeWindow?.__ERROR_REPORTER__?.(
      normalizeError(error, message),
      options.reporterMetadata ?? payload,
    )
  } else {
    console.warn(prefix, error)
  }

  runtimeWindow?.__RUNTIME_REPORTER__?.(payload)

  if (!userMessage || !shouldNotify(dedupeKey, dedupeMs)) {
    return
  }

  if (level === 'error') {
    toast.error(toastTitle ?? 'Something went wrong', {
      description: userMessage,
    })
    return
  }

  toast(toastTitle ?? 'Notice', {
    description: userMessage,
  })
}

export function reportRuntimeError(options: RuntimeReportOptions): void {
  emitRuntimeReport('error', options)
}

export function reportRuntimeWarning(options: RuntimeReportOptions): void {
  emitRuntimeReport('warn', options)
}

export function resetRuntimeNotificationThrottle(): void {
  notificationTimestamps.clear()
}
