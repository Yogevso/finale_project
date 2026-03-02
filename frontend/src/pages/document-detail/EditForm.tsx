import { useState } from 'react'
import VisibilityChangeConfirmDialog from '@/components/VisibilityChangeConfirmDialog'
import {
  getAudienceDirtyHelperText,
  getAudienceDirtyState,
  getAudienceVisibilityHelperText,
  requiresVisibilityChangeConfirmation,
} from '@/features/documents'
import type { DocumentStatus, DocumentUpdate, DocumentVisibility } from '@/types'

type PendingVisibilityConfirmation = {
  fromVisibility: DocumentVisibility
  toVisibility: DocumentVisibility
}

export function EditForm({
  document,
  onSave,
  onCancel,
  isLoading,
  canEditVisibility,
  initialCompanyIds = [],
}: {
  document: {
    title: string
    description?: string | null
    status: DocumentStatus
    visibility: DocumentVisibility
    category?: string | null
    release_branch?: string | null
    tags?: string | null
  }
  onSave: (data: DocumentUpdate) => void
  onCancel: () => void
  isLoading: boolean
  canEditVisibility: boolean
  initialCompanyIds?: number[]
}) {
  const [formData, setFormData] = useState<DocumentUpdate>({
    title: document.title,
    description: document.description || '',
    status: document.status as DocumentStatus,
    visibility: document.visibility as DocumentVisibility,
    category: document.category || '',
    release_branch: document.release_branch || '',
    tags: document.tags || '',
  })
  const [pendingVisibilityConfirmation, setPendingVisibilityConfirmation] =
    useState<PendingVisibilityConfirmation | null>(null)
  const audienceDirtyState = getAudienceDirtyState(
    {
      visibility: document.visibility,
      company_ids: [],
    },
    {
      visibility: formData.visibility ?? document.visibility,
      company_ids: [],
    },
  )
  const audienceDirtyHelper = getAudienceDirtyHelperText(audienceDirtyState)
  const visibilityHelperText = getAudienceVisibilityHelperText(
    formData.visibility ?? document.visibility,
    'edit',
  )

  const submitChanges = (companyIds?: number[]) => {
    const saveData = { ...formData }
    if (companyIds && companyIds.length > 0) {
      saveData.company_ids = companyIds
    }
    onSave(saveData)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const nextVisibility = formData.visibility ?? document.visibility
    // Always show dialog when changing to company visibility or when expanding access
    if (
      canEditVisibility &&
      (nextVisibility === 'company' ||
        requiresVisibilityChangeConfirmation(document.visibility, nextVisibility))
    ) {
      setPendingVisibilityConfirmation({
        fromVisibility: document.visibility,
        toVisibility: nextVisibility,
      })
      return
    }

    submitChanges()
  }

  const handleConfirmVisibilityChange = (companyIds?: number[]) => {
    setPendingVisibilityConfirmation(null)
    submitChanges(companyIds)
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="surface-card rounded-2xl p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="input-field"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="input-field"
            rows={4}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as DocumentStatus })}
              className="select-field"
            >
              <option value="draft">Draft</option>
              <option value="pending_review">Pending Review</option>
              <option value="approved">Approved</option>
              <option value="active">Published</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Visibility</label>
            <select
              value={formData.visibility}
              onChange={(e) =>
                setFormData({ ...formData, visibility: e.target.value as DocumentVisibility })
              }
              className="select-field disabled:opacity-60"
              disabled={!canEditVisibility}
            >
              <option value="internal">Internal (Staff only)</option>
              <option value="public">Public (Everyone)</option>
              <option value="company">Company (Assigned companies)</option>
            </select>
            <p className="text-xs text-slate-500 mt-1">{visibilityHelperText}</p>
            <p
              className={`text-xs mt-1 ${
                audienceDirtyHelper.isChanged ? 'text-amber-700' : 'text-slate-500'
              }`}
            >
              {audienceDirtyHelper.text}
            </p>
            {!canEditVisibility && (
              <p className="text-xs text-slate-500 mt-1">
                Only managers can change document visibility.
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
            <input
              type="text"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Release Branch</label>
            <input
              type="text"
              value={formData.release_branch || ''}
              onChange={(e) => setFormData({ ...formData, release_branch: e.target.value })}
              className="input-field"
              placeholder="e.g., R580"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
          <input
            type="text"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
            className="input-field"
            placeholder="Comma-separated tags"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <button type="button" onClick={onCancel} className="btn-ghost">
            Cancel
          </button>
          <button type="submit" disabled={isLoading} className="btn-primary disabled:opacity-50">
            {isLoading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>

      <VisibilityChangeConfirmDialog
        isOpen={pendingVisibilityConfirmation !== null}
        fromVisibility={pendingVisibilityConfirmation?.fromVisibility ?? document.visibility}
        toVisibility={pendingVisibilityConfirmation?.toVisibility ?? document.visibility}
        documentTitle={document.title}
        onCancel={() => setPendingVisibilityConfirmation(null)}
        onConfirm={handleConfirmVisibilityChange}
        isSubmitting={isLoading}
        initialCompanyIds={initialCompanyIds}
      />
    </>
  )
}
