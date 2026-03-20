import { useEffect, useId, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useFocusTrap } from '@/hooks/useAccessibility'

type ConfirmationDialogProps = {
  open: boolean
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning'
  isLoading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmationDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const descriptionId = useId()
  const { containerRef } = useFocusTrap(isLoading ? undefined : onCancel)

  useEffect(() => {
    if (open) {
      cancelRef.current?.focus()
    }
  }, [open])

  if (!open) return null

  const isDanger = variant === 'danger'

  return (
    <div
      className="modal-overlay flex items-center justify-center p-4"
    >
      <button
        type="button"
        className="absolute inset-0"
        onClick={isLoading ? undefined : onCancel}
        aria-label="Close confirmation dialog"
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        aria-busy={isLoading}
        tabIndex={-1}
        className="modal-content motion-enter-scale w-full max-w-md space-y-4 p-6 dark:bg-slate-900"
      >
        <div className="flex items-start gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
              isDanger ? 'bg-rose-100' : 'bg-amber-100'
            }`}
          >
            <AlertTriangle
              className={`h-5 w-5 ${isDanger ? 'text-rose-600 dark:text-rose-300' : 'text-amber-600 dark:text-amber-300'}`}
              aria-hidden="true"
            />
          </div>
          <div>
            <h3 id={titleId} className="text-lg font-display font-semibold text-slate-900 dark:text-slate-100">
              {title}
            </h3>
            {description && (
              <p id={descriptionId} className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                {description}
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="btn-ghost disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50 ${
              isDanger
                ? 'bg-rose-600 hover:bg-rose-700 hover:scale-[1.02]'
                : 'bg-amber-600 hover:bg-amber-700 hover:scale-[1.02]'
            }`}
          >
            {isLoading && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
