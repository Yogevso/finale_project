import { Send } from 'lucide-react'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface ReviewSubmitModalProps {
  isOpen: boolean
  documentTitle: string
  message: string
  onMessageChange: (value: string) => void
  onClose: () => void
  onSubmit: () => void
  isSubmitting: boolean
  errorMessage?: string | null
}

export function ReviewSubmitModal({
  isOpen,
  documentTitle,
  message,
  onMessageChange,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
}: ReviewSubmitModalProps) {
  const { containerRef, handleKeyDown } = useFocusTrap(onClose)

  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div ref={containerRef} role="dialog" aria-modal="true" aria-label="Submit for Review" className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
        <h3 className="text-lg font-display font-semibold text-slate-900 mb-4">Submit for Review</h3>
        <p className="text-sm text-slate-600 mb-4">
          This will submit "{documentTitle}" for review. A manager or peer editor can approve or
          reject it. Publishing happens later as a separate step.
        </p>
        <div className="mb-4">
          <label htmlFor="review-submit-message" className="block text-sm font-medium text-slate-700 mb-2">
            Message (optional)
          </label>
          <textarea
            id="review-submit-message"
            value={message}
            onChange={(event) => onMessageChange(event.target.value)}
            placeholder="Add a note for the reviewer..."
            rows={3}
            className="input-field"
          />
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} disabled={isSubmitting} className="btn-ghost">
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={isSubmitting}
            className="btn-primary flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {isSubmitting ? 'Submitting...' : 'Submit'}
          </button>
        </div>
        {errorMessage && <p className="mt-3 text-sm text-rose-600">{errorMessage}</p>}
      </div>
    </div>
  )
}
