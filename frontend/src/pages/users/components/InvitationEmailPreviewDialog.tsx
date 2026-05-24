import { Mail, RefreshCw, X } from 'lucide-react'
import { useId } from 'react'

import { useFocusTrap } from '@/hooks/useAccessibility'
import type { Invitation, InvitationEmailPreviewResponse } from '@/types'

import { getInvitationDeliveryBadgeColor } from '../constants'

interface InvitationEmailPreviewDialogProps {
  open: boolean
  invitation: Invitation | null
  preview?: InvitationEmailPreviewResponse
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  onClose: () => void
}

function formatSender(preview: InvitationEmailPreviewResponse | undefined) {
  if (!preview) return '-'
  return `${preview.from_name} <${preview.from_email}>`
}

export function InvitationEmailPreviewDialog({
  open,
  invitation,
  preview,
  isLoading,
  isError,
  onRetry,
  onClose,
}: InvitationEmailPreviewDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const { containerRef } = useFocusTrap<HTMLDivElement>(isLoading ? undefined : onClose)

  if (!open || !invitation) {
    return null
  }

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        aria-label="Close invitation email preview"
        onClick={isLoading ? undefined : onClose}
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        className="modal-content motion-enter-scale flex max-h-[90vh] w-full max-w-5xl flex-col gap-5 overflow-hidden p-6 dark:bg-slate-900"
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Mail className="h-5 w-5 text-blue-600 dark:text-blue-300" />
              <h3
                id={titleId}
                className="text-lg font-display font-semibold text-slate-900 dark:text-slate-100"
              >
                Invitation Email Preview
              </h3>
              <span
                className={`pill capitalize ${getInvitationDeliveryBadgeColor(
                  invitation.email_delivery_status,
                )}`}
              >
                {invitation.email_delivery_status}
              </span>
            </div>
            <p id={descriptionId} className="text-sm text-slate-600 dark:text-slate-300">
              Safe preview for {invitation.email}. The invitation link is redacted and cannot be
              used.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="admin-icon-action shrink-0"
            aria-label="Close invitation email preview"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex min-h-[320px] items-center justify-center">
            <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700 dark:border-slate-700 dark:border-t-slate-200" />
              Loading preview...
            </div>
          </div>
        ) : isError || !preview ? (
          <div className="flex min-h-[320px] flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center dark:border-slate-700 dark:bg-slate-950/60">
            <p className="max-w-md text-sm text-slate-600 dark:text-slate-300">
              The preview could not be loaded. Retry to fetch the latest invitation email content.
            </p>
            <button type="button" onClick={onRetry} className="btn-secondary table-action-btn">
              <RefreshCw className="h-4 w-4" />
              Retry Preview
            </button>
          </div>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  From
                </p>
                <p className="mt-2 text-sm text-slate-900 dark:text-slate-100">
                  {formatSender(preview)}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  To
                </p>
                <p className="mt-2 text-sm text-slate-900 dark:text-slate-100">{preview.email}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Subject
                </p>
                <p className="mt-2 text-sm text-slate-900 dark:text-slate-100">
                  {preview.subject}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Preview Link
                </p>
                <p className="mt-2 break-all text-xs text-slate-700 dark:text-slate-300">
                  {preview.preview_accept_url}
                </p>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.35fr_0.9fr]">
              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950/70">
                <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    HTML Preview
                  </h4>
                </div>
                <div
                  className="max-h-[420px] overflow-auto px-5 py-4 text-sm text-slate-700 dark:text-slate-200"
                  dangerouslySetInnerHTML={{ __html: preview.html_content }}
                />
              </section>

              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950/60">
                <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Plain Text
                  </h4>
                </div>
                <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap break-words px-4 py-4 text-xs text-slate-700 dark:text-slate-300">
                  {preview.text_content || 'No plain-text body returned.'}
                </pre>
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
