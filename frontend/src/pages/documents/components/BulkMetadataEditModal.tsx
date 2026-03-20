import { useState } from 'react'
import { X } from 'lucide-react'
import CompanySelector from '@/components/CompanySelector'
import type { BulkDocumentMetadataUpdate, DocumentVisibility } from '@/types'
import { useFocusTrap } from '@/hooks/useAccessibility'

type BulkMetadataEditModalProps = {
  selectedCount: number
  isSubmitting: boolean
  onClose: () => void
  onSubmit: (payload: BulkDocumentMetadataUpdate) => void
  documentIds: number[]
}

export function BulkMetadataEditModal({
  selectedCount,
  isSubmitting,
  onClose,
  onSubmit,
  documentIds,
}: BulkMetadataEditModalProps) {
  const [category, setCategory] = useState('')
  const [visibility, setVisibility] = useState<DocumentVisibility | ''>('')
  const [companyIds, setCompanyIds] = useState<number[]>([])
  const [reason, setReason] = useState('')
  const { containerRef } = useFocusTrap<HTMLDivElement>(onClose)

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-transparent"
        onClick={onClose}
        aria-label="Close bulk edit metadata dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Bulk Edit Metadata"
        tabIndex={-1}
        className="modal-content relative z-10 w-full max-w-xl"
      >
        <div className="flex items-center justify-between border-b border-slate-200 p-5">
          <div>
            <h2 className="section-title text-xl">Bulk Edit Metadata</h2>
            <p className="body-copy">Apply one metadata update to {selectedCount} documents.</p>
          </div>
          <button type="button" onClick={onClose} className="btn-icon h-9 w-9 text-slate-500 hover:bg-slate-100" aria-label="Close bulk edit dialog">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          <div>
            <label htmlFor="bulk-metadata-category" className="mb-1 block text-sm font-medium text-slate-700">Category</label>
            <input
              id="bulk-metadata-category"
              type="text"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="input-field"
              placeholder="Leave blank to keep current value"
            />
          </div>

          <div>
            <label htmlFor="bulk-metadata-visibility" className="mb-1 block text-sm font-medium text-slate-700">Visibility</label>
            <select
              id="bulk-metadata-visibility"
              value={visibility}
              onChange={(event) => setVisibility(event.target.value as DocumentVisibility | '')}
              className="select-field"
            >
              <option value="">Keep current visibility</option>
              <option value="internal">Internal</option>
              <option value="public">Public</option>
              <option value="company">Company</option>
            </select>
          </div>

          {visibility === 'company' ? (
            <div>
              <p className="mb-1 block text-sm font-medium text-slate-700">Assigned Companies</p>
              <CompanySelector
                selectedIds={companyIds}
                onChange={setCompanyIds}
                placeholder="Select companies for the selected documents..."
              />
            </div>
          ) : null}

          {visibility ? (
            <div>
              <label htmlFor="bulk-metadata-reason" className="mb-1 block text-sm font-medium text-slate-700">Reason</label>
              <textarea
                id="bulk-metadata-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                className="input-field"
                rows={3}
                placeholder="Explain why this visibility update is needed"
              />
              <p className="mt-1 text-xs text-slate-500">Minimum 3 characters required.</p>
            </div>
          ) : null}
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-200 p-5">
          <button type="button" onClick={onClose} className="btn-ghost table-action-btn">
            Cancel
          </button>
          <button
            type="button"
            disabled={
              isSubmitting ||
              (category.trim() === '' && visibility === '' && companyIds.length === 0) ||
              (visibility !== '' && reason.trim().length < 3) ||
              (visibility === 'company' && companyIds.length === 0)
            }
            className="btn-primary table-action-btn disabled:opacity-60"
            onClick={() =>
              onSubmit({
                document_ids: documentIds,
                category: category.trim() || undefined,
                visibility: visibility || undefined,
                company_ids: companyIds.length > 0 ? companyIds : undefined,
                reason: reason.trim() || undefined,
              })
            }
          >
            {isSubmitting ? 'Updating...' : 'Apply changes'}
          </button>
          {!isSubmitting && (
            <p className="helper-copy mt-1 text-right">
              {category.trim() === '' && visibility === '' && companyIds.length === 0
                ? 'Select at least one field to update.'
                : visibility !== '' && reason.trim().length < 3
                  ? 'Reason must be at least 3 characters.'
                  : visibility === 'company' && companyIds.length === 0
                    ? 'Select at least one target company.'
                    : ''}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
