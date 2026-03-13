import { useState } from 'react'
import CompanySelector from '@/components/CompanySelector'
import type { BulkDocumentMetadataUpdate, DocumentVisibility } from '@/types'

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-xl rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 p-5">
          <div>
            <h2 className="text-xl font-display font-bold text-slate-900">Bulk Edit Metadata</h2>
            <p className="text-sm text-slate-500">Apply one metadata update to {selectedCount} documents.</p>
          </div>
          <button onClick={onClose} className="rounded-xl p-2 text-slate-500 hover:bg-slate-100">
            x
          </button>
        </div>

        <div className="space-y-4 p-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Category</label>
            <input
              type="text"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="input-field"
              placeholder="Leave blank to keep current value"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Visibility</label>
            <select
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
              <label className="mb-1 block text-sm font-medium text-slate-700">Assigned Companies</label>
              <CompanySelector
                selectedIds={companyIds}
                onChange={setCompanyIds}
                placeholder="Select companies for the selected documents..."
              />
            </div>
          ) : null}

          {visibility ? (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Reason</label>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                className="input-field"
                rows={3}
                placeholder="Explain why this visibility update is needed"
              />
            </div>
          ) : null}
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-200 p-5">
          <button type="button" onClick={onClose} className="btn-ghost">
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
            className="btn-primary disabled:opacity-60"
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
        </div>
      </div>
    </div>
  )
}
