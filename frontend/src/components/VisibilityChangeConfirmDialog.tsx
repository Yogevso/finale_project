import { useState, useEffect, useRef, useId } from 'react'
import { getVisibilityLabel } from '@/features/documents'
import {
  COMMUNICATION_INPUT_LIMITS,
  normalizeMultilineInput,
} from '@/lib/uiInputRules'
import type { DocumentVisibility } from '@/types'
import CompanySelector from './CompanySelector'
import { useFocusTrap } from '@/hooks/useAccessibility'

type VisibilityChangeConfirmDialogProps = {
  isOpen: boolean
  fromVisibility: DocumentVisibility
  toVisibility: DocumentVisibility
  documentTitle?: string
  onCancel: () => void
  onConfirm: (result: { reason: string; companyIds?: number[] }) => void
  isSubmitting?: boolean
  initialCompanyIds?: number[]
}

export default function VisibilityChangeConfirmDialog({
  isOpen,
  fromVisibility,
  toVisibility,
  documentTitle,
  onCancel,
  onConfirm,
  isSubmitting = false,
  initialCompanyIds = [],
}: VisibilityChangeConfirmDialogProps) {
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<number[]>(initialCompanyIds)
  const [reason, setReason] = useState('')
  const wasOpenRef = useRef(false)
  const titleId = useId()
  const descriptionId = useId()
  const companySelectorLabelId = useId()
  const reasonHintId = useId()
  const reasonErrorId = useId()

  const { containerRef } = useFocusTrap(onCancel)

  // Only reset selection when dialog opens (transitions from closed to open)
  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      setSelectedCompanyIds(initialCompanyIds)
      setReason('')
    }
    wasOpenRef.current = isOpen
  }, [isOpen, initialCompanyIds])

  if (!isOpen) {
    return null
  }

  const fromLabel = getVisibilityLabel(fromVisibility)
  const toLabel = getVisibilityLabel(toVisibility)
  const documentLabel = documentTitle ? `"${documentTitle}"` : 'this document'
  const isCompanyVisibility = toVisibility === 'company'
  const reasonIsValid = reason.trim().length >= 3
  const canConfirm = reasonIsValid && (!isCompanyVisibility || selectedCompanyIds.length > 0)
  const showReasonError = reason.length > 0 && !reasonIsValid

  const handleConfirm = () => {
    const normalizedReason = normalizeMultilineInput(
      reason,
      COMMUNICATION_INPUT_LIMITS.visibilityReason,
    )
    onConfirm({
      reason: normalizedReason,
      companyIds: isCompanyVisibility ? selectedCompanyIds : undefined,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
        aria-label="Close visibility change dialog"
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        className="relative w-full max-w-lg space-y-4 overflow-visible rounded-2xl bg-white p-6 shadow-xl"
      >
        <div>
          <h3 id={titleId} className="text-lg font-display font-semibold text-slate-900">
            Confirm Visibility Change
          </h3>
          <p id={descriptionId} className="mt-2 text-sm text-slate-600">
            You are expanding access for {documentLabel} from{' '}
            <span className="font-medium text-slate-900">{fromLabel}</span> to{' '}
            <span className="font-medium text-slate-900">{toLabel}</span>.
          </p>
          <p className="mt-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl p-3">
            This may expose content to a broader audience. Continue only if this is intended.
          </p>
        </div>

        {isCompanyVisibility && (
          <div className="space-y-2">
            <p id={companySelectorLabelId} className="block text-sm font-medium text-slate-700">
              Select companies to grant access <span className="text-rose-500">*</span>
            </p>
            <div aria-labelledby={companySelectorLabelId} role="group">
              <CompanySelector
                selectedIds={selectedCompanyIds}
                onChange={setSelectedCompanyIds}
                placeholder="Select companies..."
                disabled={isSubmitting}
              />
            </div>
            {selectedCompanyIds.length === 0 && (
              <p className="text-xs text-amber-600">
                At least one company must be selected for company visibility.
              </p>
            )}
            {selectedCompanyIds.length > 0 && (
              <p className="text-xs text-slate-500">
                {selectedCompanyIds.length} company(s) will have access to this document.
              </p>
            )}
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="visibility-reason" className="block text-sm font-medium text-slate-700">
            Reason for change <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="visibility-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="input-field min-h-[92px]"
            placeholder="Describe why this visibility change is required..."
            disabled={isSubmitting}
            maxLength={COMMUNICATION_INPUT_LIMITS.visibilityReason}
            data-testid="visibility-change-reason"
            aria-invalid={showReasonError}
            aria-describedby={showReasonError ? `${reasonHintId} ${reasonErrorId}` : reasonHintId}
          />
          <p id={reasonHintId} className="text-xs text-slate-500">
            Minimum 3 characters. Reason is stored in the audience audit trail. {reason.length}/
            {COMMUNICATION_INPUT_LIMITS.visibilityReason}
          </p>
          {showReasonError ? (
            <p id={reasonErrorId} role="alert" className="text-xs text-rose-600">
              Enter at least 3 characters so the audit trail has a meaningful reason.
            </p>
          ) : null}
        </div>

        <div className="flex justify-end gap-3 pt-1">
          <button type="button" onClick={onCancel} className="btn-ghost" disabled={isSubmitting}>
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="btn-primary disabled:opacity-50"
            disabled={isSubmitting || !canConfirm}
          >
            {isSubmitting ? 'Applying...' : 'Confirm Change'}
          </button>
        </div>
      </div>
    </div>
  )
}
