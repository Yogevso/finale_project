import { getVisibilityLabel } from '@/features/documents'
import type { DocumentVisibility } from '@/types'

type VisibilityChangeConfirmDialogProps = {
  isOpen: boolean
  fromVisibility: DocumentVisibility
  toVisibility: DocumentVisibility
  documentTitle?: string
  onCancel: () => void
  onConfirm: () => void
  isSubmitting?: boolean
}

export default function VisibilityChangeConfirmDialog({
  isOpen,
  fromVisibility,
  toVisibility,
  documentTitle,
  onCancel,
  onConfirm,
  isSubmitting = false,
}: VisibilityChangeConfirmDialogProps) {
  if (!isOpen) {
    return null
  }

  const fromLabel = getVisibilityLabel(fromVisibility)
  const toLabel = getVisibilityLabel(toVisibility)
  const documentLabel = documentTitle ? `"${documentTitle}"` : 'this document'

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl p-6 space-y-4">
        <div>
          <h3 className="text-lg font-display font-semibold text-slate-900">
            Confirm Visibility Change
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            You are expanding access for {documentLabel} from{' '}
            <span className="font-medium text-slate-900">{fromLabel}</span> to{' '}
            <span className="font-medium text-slate-900">{toLabel}</span>.
          </p>
          <p className="mt-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl p-3">
            This may expose content to a broader audience. Continue only if this is intended.
          </p>
        </div>

        <div className="flex justify-end gap-3 pt-1">
          <button type="button" onClick={onCancel} className="btn-ghost" disabled={isSubmitting}>
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="btn-primary disabled:opacity-50"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Applying...' : 'Confirm Change'}
          </button>
        </div>
      </div>
    </div>
  )
}
