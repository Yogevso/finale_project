import { toast } from 'sonner'

type ToastDescription = string | undefined

type ApiLikeError = {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

export function extractApiErrorMessage(error: unknown, fallback: string): string {
  const apiError = error as ApiLikeError
  return apiError.response?.data?.detail || apiError.message || fallback
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
