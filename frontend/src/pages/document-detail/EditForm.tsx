import { useEffect, useState } from 'react'
import VisibilityChangeConfirmDialog from '@/components/VisibilityChangeConfirmDialog'
import {
  getAudienceDirtyHelperText,
  getAudienceDirtyState,
  getAudienceVisibilityHelperText,
} from '@/features/documents'
import type { DocumentStatus, DocumentUpdate, DocumentVisibility } from '@/types'

type PendingVisibilityConfirmation = {
  fromVisibility: DocumentVisibility
  toVisibility: DocumentVisibility
}

type VisibilityChangeDialogResult = {
  reason: string
  companyIds?: number[]
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
    due_date?: string | null
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
    visibility: document.visibility as DocumentVisibility,
    category: document.category || '',
    release_branch: document.release_branch || '',
    tags: document.tags || '',
    due_date: document.due_date || '',
  })
  const [pendingVisibilityConfirmation, setPendingVisibilityConfirmation] =
    useState<PendingVisibilityConfirmation | null>(null)

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const isDirty =
      formData.title !== document.title ||
      (formData.description || '') !== (document.description || '') ||
      formData.visibility !== document.visibility ||
      (formData.category || '') !== (document.category || '') ||
      (formData.release_branch || '') !== (document.release_branch || '') ||
      (formData.tags || '') !== (document.tags || '') ||
      (formData.due_date || '') !== (document.due_date || '')

    if (!isDirty) return

    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [formData, document])

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
  const workflowStatusLabel =
    document.status === 'active'
      ? 'Published'
      : document.status === 'pending_review'
        ? 'Pending Review'
        : document.status === 'approved'
          ? 'Approved'
          : document.status === 'archived'
            ? 'Archived'
            : 'Draft'

  const submitChanges = (reason?: string, companyIds?: number[]) => {
    const saveData = { ...formData }
    if (reason && reason.trim().length > 0) {
      saveData.reason = reason.trim()
    }
    if (companyIds && companyIds.length > 0) {
      saveData.company_ids = companyIds
    }
    onSave(saveData)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const nextVisibility = formData.visibility ?? document.visibility
    // Wave T reason-capture policy: all visibility changes require a reason.
    if (canEditVisibility && nextVisibility !== document.visibility) {
      setPendingVisibilityConfirmation({
        fromVisibility: document.visibility,
        toVisibility: nextVisibility,
      })
      return
    }

    submitChanges()
  }

  const handleConfirmVisibilityChange = ({ reason, companyIds }: VisibilityChangeDialogResult) => {
    setPendingVisibilityConfirmation(null)
    submitChanges(reason, companyIds)
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="surface-card rounded-2xl p-6 space-y-4">
        <div>
          <label htmlFor="document-edit-title" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
            Title
          </label>
          <input
            id="document-edit-title"
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="input-field"
            required
          />
        </div>

        <div>
          <label htmlFor="document-edit-description" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
            Description
          </label>
          <textarea
            id="document-edit-description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="input-field"
            rows={4}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="helper-copy mb-1 block font-medium uppercase tracking-wide">
              Workflow Status
            </label>
            <div className="input-field flex min-h-11 items-center bg-slate-50 text-slate-700">
              {workflowStatusLabel}
            </div>
            <p className="helper-copy mt-1">
              Status changes are controlled by review, publish, archive, and restore actions.
            </p>
          </div>
          <div>
            <label htmlFor="document-edit-visibility" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
              Visibility
            </label>
            <select
              id="document-edit-visibility"
              name="visibility"
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
            <p className="helper-copy mt-1">{visibilityHelperText}</p>
            <p
              className={`helper-copy mt-1 ${
                audienceDirtyHelper.isChanged ? 'text-amber-700' : 'text-slate-500'
              }`}
            >
              {audienceDirtyHelper.text}
            </p>
            {!canEditVisibility && (
              <p className="helper-copy mt-1">
                Only managers can change document visibility.
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="document-edit-category" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
              Category
            </label>
            <input
              id="document-edit-category"
              type="text"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label htmlFor="document-edit-release-branch" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
              Release Branch
            </label>
            <input
              id="document-edit-release-branch"
              type="text"
              value={formData.release_branch || ''}
              onChange={(e) => setFormData({ ...formData, release_branch: e.target.value })}
              className="input-field"
              placeholder="e.g., R580"
            />
          </div>
        </div>

        <div>
          <label htmlFor="document-edit-due-date" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
            Due Date
          </label>
          <input
            id="document-edit-due-date"
            type="date"
            value={formData.due_date || ''}
            min={new Date().toISOString().split('T')[0]}
            onChange={(e) => setFormData({ ...formData, due_date: e.target.value || null })}
            className="input-field"
          />
        </div>

        <div>
          <label htmlFor="document-edit-tags" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
            Tags
          </label>
          <input
            id="document-edit-tags"
            type="text"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
            className="input-field"
            placeholder="Comma-separated tags"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <button type="button" onClick={onCancel} className="btn-ghost table-action-btn">
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary table-action-btn disabled:opacity-50"
          >
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
