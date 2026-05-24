import { toast } from 'sonner'

type ToastDescription = string | undefined

type ApiLikeError = {
  response?: {
    status?: number
    headers?: Record<string, unknown>
    data?: {
      detail?: unknown
      message?: unknown
      error?: unknown
      error_code?: unknown
    }
  }
  message?: unknown
}

function extractErrorText(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : null
  }

  if (value && typeof value === 'object') {
    const nested = value as {
      detail?: unknown
      message?: unknown
      error?: unknown
      errors?: unknown
    }
    return (
      extractErrorText(nested.detail) ||
      extractErrorText(nested.message) ||
      extractErrorText(nested.error) ||
      extractErrorText(nested.errors)
    )
  }

  return null
}

function extractTraceId(headers?: Record<string, unknown>): string | null {
  if (!headers) {
    return null
  }
  const candidateKeys = ['x-request-id', 'x-trace-id', 'x-correlation-id']
  for (const key of candidateKeys) {
    const value = headers[key]
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
    if (Array.isArray(value) && typeof value[0] === 'string' && value[0].trim()) {
      return value[0].trim()
    }
  }
  return null
}

function mapErrorCodeToMessage(errorCode: string): string | null {
  switch (errorCode) {
    case 'precondition_required':
      return 'Your data is outdated. Refresh and try again.'
    case 'conflict':
      return 'The data changed on the server. Refresh and retry.'
    case 'missing_company_assignment':
      return 'At least one company must be assigned before continuing.'
    case 'invalid_company_set':
      return 'One or more selected companies are invalid.'
    default:
      return null
  }
}

export function extractApiErrorMessage(error: unknown, fallback: string): string {
  const apiError = error as ApiLikeError
  const status = apiError.response?.status
  const errorCodeRaw = apiError.response?.data?.error_code
  const errorCode = typeof errorCodeRaw === 'string' ? errorCodeRaw : null
  const detail =
    extractErrorText(apiError.response?.data?.detail) ||
    extractErrorText(apiError.response?.data?.message) ||
    extractErrorText(apiError.response?.data?.error) ||
    extractErrorText(apiError.message)

  let message =
    detail ||
    (errorCode ? mapErrorCodeToMessage(errorCode) : null) ||
    (status === 401 || status === 403
      ? 'Session expired. Please sign in again.'
      : status === 409
        ? 'Request conflicted with newer data. Refresh and retry.'
        : null) ||
    fallback

  const traceId = extractTraceId(apiError.response?.headers)
  if (traceId && !message.includes(traceId)) {
    message = `${message} (Ref: ${traceId})`
  }

  return message
}

export function useToast() {
  return {
    success(message: string, description?: ToastDescription) {
      toast.success(message, { description })
    },
    error(message: string, description?: ToastDescription) {
      toast.error(message, { description })
    },
    info(message: string, description?: ToastDescription) {
      toast(message, { description })
    },
  }
}
