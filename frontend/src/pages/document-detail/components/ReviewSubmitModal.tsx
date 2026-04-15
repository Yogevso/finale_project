import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Send, X } from 'lucide-react'
import VersionDiffView from '@/components/VersionDiffView'
import { useFocusTrap } from '@/hooks/useAccessibility'
import { api } from '@/lib/api'
import { getUsableVersionContent } from '@/pages/document-detail/helpers/previewHelpers'

interface ReviewSubmitModalProps {
  isOpen: boolean
  documentId: number
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
  documentId,
  documentTitle,
  message,
  onMessageChange,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
}: ReviewSubmitModalProps) {
  const { containerRef } = useFocusTrap<HTMLDivElement>(onClose)
  const [showDiff, setShowDiff] = useState(false)
  const [publishedHtml, setPublishedHtml] = useState<string | null>(null)
  const [latestHtml, setLatestHtml] = useState<string | null>(null)
  const [loadingDiff, setLoadingDiff] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setShowDiff(false)
      setPublishedHtml(null)
      setLatestHtml(null)
      return
    }

    let cancelled = false
    async function loadVersions() {
      setLoadingDiff(true)
      try {
        const versions = await api.getVersions(documentId)
        if (cancelled) return
        const sorted = [...versions.items].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
        const latest = sorted[0]
        const published = sorted.find((v) => v.is_published)

        setLatestHtml(latest ? getUsableVersionContent(latest.content) : null)
        setPublishedHtml(published && published.id !== latest?.id ? getUsableVersionContent(published.content) : null)
      } catch {
        // silently fail — diff is optional
      } finally {
        if (!cancelled) setLoadingDiff(false)
      }
    }

    void loadVersions()
    return () => { cancelled = true }
  }, [isOpen, documentId])

  if (!isOpen) {
    return null
  }

  const hasDiffData = publishedHtml !== null && latestHtml !== null

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-transparent"
        onClick={isSubmitting ? undefined : onClose}
        disabled={isSubmitting}
        aria-label="Close submit for review dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Submit for Review"
        tabIndex={-1}
        className={`modal-content relative z-10 w-full p-6 ${hasDiffData ? 'max-w-4xl' : 'max-w-md'}`}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="section-title text-xl">Submit for Review</h3>
            <p className="body-copy mt-1">
              This will submit "{documentTitle}" for review. A manager or peer editor can approve
              or reject it. Publishing happens later as a separate step.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="btn-icon h-9 w-9 text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Close submit review dialog"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Diff view toggle */}
        {hasDiffData && (
          <div className="mt-4">
            <button
              type="button"
              onClick={() => setShowDiff(!showDiff)}
              className="flex items-center gap-2 text-sm font-medium text-sky-600 hover:text-sky-800"
            >
              {showDiff ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              {showDiff ? 'Hide changes' : 'View changes since last published version'}
            </button>
            {showDiff && (
              <div className="mt-3 max-h-[50vh] overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-4">
                <VersionDiffView
                  leftHtml={publishedHtml}
                  rightHtml={latestHtml}
                  leftLabel="Published Version"
                  rightLabel="Current Version"
                />
              </div>
            )}
          </div>
        )}

        {loadingDiff && (
          <p className="body-copy mt-3 text-slate-400">Loading version comparison...</p>
        )}

        <div className="mt-6">
          <label
            htmlFor="review-submit-message"
            className="helper-copy mb-2 block font-medium uppercase tracking-wide"
          >
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

        {errorMessage ? (
          <p className="alert-danger body-copy mt-4" role="alert">
            {errorMessage}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="btn-ghost table-action-btn"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={isSubmitting}
            className="btn-primary table-action-btn flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {isSubmitting ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>
    </div>
  )
}
