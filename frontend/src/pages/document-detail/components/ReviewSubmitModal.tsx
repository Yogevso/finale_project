import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Send, X } from 'lucide-react'
import VersionDiffView from '@/components/VersionDiffView'
import { useFocusTrap } from '@/hooks/useAccessibility'
import { api } from '@/lib/api'
import { getUsableVersionContent } from '@/pages/document-detail/helpers/previewHelpers'
import type { User } from '@/types'

interface ReviewSubmitModalProps {
  isOpen: boolean
  documentId: number
  documentTitle: string
  message: string
  onMessageChange: (value: string) => void
  onClose: () => void
  onSubmit: (requestedReviewerIds: number[]) => void
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
  const [reviewerCandidates, setReviewerCandidates] = useState<User[]>([])
  const [selectedReviewerIds, setSelectedReviewerIds] = useState<number[]>([])
  const [loadingReviewers, setLoadingReviewers] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setShowDiff(false)
      setPublishedHtml(null)
      setLatestHtml(null)
      setSelectedReviewerIds([])
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

  useEffect(() => {
    if (!isOpen) {
      setReviewerCandidates([])
      setLoadingReviewers(false)
      return
    }

    let cancelled = false
    async function loadReviewerCandidates() {
      setLoadingReviewers(true)
      try {
        const candidates = await api.getReviewerCandidates(documentId)
        if (cancelled) return
        setReviewerCandidates(candidates)
      } catch {
        if (cancelled) return
        setReviewerCandidates([])
      } finally {
        if (!cancelled) setLoadingReviewers(false)
      }
    }

    void loadReviewerCandidates()
    return () => {
      cancelled = true
    }
  }, [documentId, isOpen])

  if (!isOpen) {
    return null
  }

  const hasDiffData = publishedHtml !== null && latestHtml !== null

  const toggleReviewerSelection = (reviewerId: number) => {
    setSelectedReviewerIds((currentIds) => {
      if (currentIds.includes(reviewerId)) {
        return currentIds.filter((id) => id !== reviewerId)
      }
      return [...currentIds, reviewerId]
    })
  }

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
              className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800"
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

        <div className="mt-5">
          <p className="helper-copy mb-2 block font-medium uppercase tracking-wide">
            Requested reviewers (optional)
          </p>
          <p className="body-copy mb-3 text-sm text-slate-500">
            Choose specific reviewers or leave empty to route using ownership rules.
          </p>
          <div className="max-h-44 overflow-auto rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900/60">
            {loadingReviewers ? (
              <p className="body-copy text-slate-400">Loading reviewers...</p>
            ) : reviewerCandidates.length === 0 ? (
              <p className="body-copy text-slate-400">
                No explicit reviewer candidates found for this document.
              </p>
            ) : (
              <div className="space-y-2">
                {reviewerCandidates.map((reviewer) => (
                  <label
                    key={reviewer.id}
                    className="flex cursor-pointer items-center justify-between rounded-lg px-2 py-2 text-sm transition hover:bg-slate-50 dark:hover:bg-slate-800/70"
                  >
                    <span className="text-slate-700 dark:text-slate-200">
                      {reviewer.full_name}
                      <span className="ml-2 text-xs uppercase tracking-wide text-slate-400">
                        {reviewer.role.replace('_', ' ')}
                      </span>
                    </span>
                    <input
                      type="checkbox"
                      checked={selectedReviewerIds.includes(reviewer.id)}
                      onChange={() => toggleReviewerSelection(reviewer.id)}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                  </label>
                ))}
              </div>
            )}
          </div>
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
            onClick={() => onSubmit(selectedReviewerIds)}
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
