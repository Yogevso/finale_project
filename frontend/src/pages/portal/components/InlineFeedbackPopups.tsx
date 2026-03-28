import { Loader2, MessageSquarePlus, Send, X } from 'lucide-react'

export interface SelectionPopupState {
  show: boolean
  x: number
  y: number
  text: string
}

export interface InlineFeedbackPopupState {
  show: boolean
  x: number
  y: number
  text: string
}

interface InlineFeedbackPopupsProps {
  selectionPopup: SelectionPopupState
  feedbackPopup: InlineFeedbackPopupState
  feedbackType: 'question' | 'suggestion' | 'issue' | 'other'
  feedbackContent: string
  validationError: string
  isSubmitting: boolean
  topOffset?: number
  onOpenFeedbackForm: () => void
  onCloseFeedbackPopup: () => void
  onFeedbackTypeChange: (value: 'question' | 'suggestion' | 'issue' | 'other') => void
  onFeedbackContentChange: (value: string) => void
  onSubmitFeedback: () => void
}

const feedbackTypeOptions = [
  { value: 'question', label: 'Question' },
  { value: 'suggestion', label: 'Suggestion' },
  { value: 'issue', label: 'Issue' },
  { value: 'other', label: 'Other' },
] as const

export function InlineFeedbackPopups({
  selectionPopup,
  feedbackPopup,
  feedbackType,
  feedbackContent,
  validationError,
  isSubmitting,
  topOffset = 0,
  onOpenFeedbackForm,
  onCloseFeedbackPopup,
  onFeedbackTypeChange,
  onFeedbackContentChange,
  onSubmitFeedback,
}: InlineFeedbackPopupsProps) {
  return (
    <>
      {selectionPopup.show && !feedbackPopup.show ? (
        <div
          className="fixed z-50 -translate-x-1/2 -translate-y-full transform"
          style={{ left: selectionPopup.x, top: Math.max(selectionPopup.y, topOffset + 12) }}
        >
          <button
            type="button"
            onClick={onOpenFeedbackForm}
            className="btn-warning table-action-btn inline-flex items-center gap-1 shadow-lg"
          >
            <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
            Add Feedback
          </button>
          <div className="absolute left-1/2 top-full -translate-x-1/2 transform">
            <div className="h-0 w-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-amber-500" />
          </div>
        </div>
      ) : null}

      {feedbackPopup.show ? (
        <div
          className="inline-comment-popup fixed z-50 -translate-x-1/2 transform"
          style={{
            left: Math.max(220, Math.min(feedbackPopup.x, window.innerWidth - 220)),
            top: Math.max(feedbackPopup.y, topOffset + 24),
          }}
        >
          <div className="surface-card w-[26rem] max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl shadow-2xl">
            <div className="border-b border-amber-100 bg-amber-50 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="helper-copy mb-1 font-medium uppercase tracking-wide text-amber-800">
                    Feedback on selection
                  </p>
                  <p className="body-copy line-clamp-3 italic text-amber-700">
                    "{feedbackPopup.text.slice(0, 160)}
                    {feedbackPopup.text.length > 160 ? '...' : ''}"
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onCloseFeedbackPopup}
                  className="btn-icon h-8 w-8 border-0 bg-transparent text-amber-600 hover:bg-amber-100 hover:text-amber-800"
                  aria-label="Close feedback popup"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-3 p-4">
              <label className="block">
                <span className="helper-copy mb-1 block">Feedback type</span>
                <select
                  value={feedbackType}
                  onChange={(event) =>
                    onFeedbackTypeChange(
                      event.target.value as 'question' | 'suggestion' | 'issue' | 'other',
                    )
                  }
                  className="select-field w-full"
                >
                  {feedbackTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="helper-copy mb-1 block">Your feedback</span>
                <textarea
                  value={feedbackContent}
                  onChange={(event) => onFeedbackContentChange(event.target.value)}
                  placeholder="Describe what should change or what needs clarification..."
                  className="input-field resize-none"
                  rows={4}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                      onSubmitFeedback()
                    }
                    if (event.key === 'Escape') {
                      onCloseFeedbackPopup()
                    }
                  }}
                />
              </label>

              {validationError ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {validationError}
                </div>
              ) : null}

              <div className="flex items-center justify-between gap-3">
                <p className="helper-copy">Press Ctrl+Enter to send</p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onCloseFeedbackPopup}
                    className="btn-ghost table-action-btn"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={onSubmitFeedback}
                    disabled={isSubmitting || feedbackContent.trim().length < 10}
                    className="btn-warning table-action-btn flex items-center gap-1 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5" />
                        Send Feedback
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="absolute left-1/2 -top-2 -translate-x-1/2 transform">
            <div className="h-0 w-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-white" />
          </div>
        </div>
      ) : null}
    </>
  )
}
