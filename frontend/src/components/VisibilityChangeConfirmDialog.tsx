import { useState, useEffect, useRef } from 'react'
import { getVisibilityLabel } from '@/features/documents'
import type { DocumentVisibility } from '@/types'
import CompanySelector from './CompanySelector'

type VisibilityChangeConfirmDialogProps = {
  isOpen: boolean
  fromVisibility: DocumentVisibility
  toVisibility: DocumentVisibility
  documentTitle?: string
  onCancel: () => void
  onConfirm: (companyIds?: number[]) => void
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
  const wasOpenRef = useRef(false)

  // Only reset selection when dialog opens (transitions from closed to open)
  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      setSelectedCompanyIds(initialCompanyIds)
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
  const canConfirm = !isCompanyVisibility || selectedCompanyIds.length > 0

  const handleConfirm = () => {
    if (isCompanyVisibility) {
      onConfirm(selectedCompanyIds)
    } else {
      onConfirm()
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div
        className="w-full max-w-lg rounded-2xl bg-white shadow-xl p-6 space-y-4 overflow-visible"
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
      >
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

        {isCompanyVisibility && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              Select companies to grant access <span className="text-rose-500">*</span>
            </label>
            <CompanySelector
              selectedIds={selectedCompanyIds}
              onChange={setSelectedCompanyIds}
              placeholder="Select companies..."
              disabled={isSubmitting}
            />
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
