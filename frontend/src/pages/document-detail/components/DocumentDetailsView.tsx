import CompanySelector from '@/components/CompanySelector'
import TagEditor from '@/components/TagEditor'
import VisibilityBadge from '@/components/VisibilityBadge'
import { formatDate } from '@/lib/dateUtils'
import { formatDueDate, isOverdueDueDate } from '@/lib/documentDueDates'
import type { AudienceAccessPreview, Company, Document, ReviewRequest } from '@/types'
import { AlertTriangle, Building2, CheckCircle, Clock, History, X, XCircle } from 'lucide-react'

interface DocumentDetailsViewProps {
  document: Document
  isEditor: boolean
  showCompanySelector: boolean
  onToggleCompanySelector: () => void
  assignedCompanies: Company[]
  assignmentDraftIds: number[]
  hasUnsavedAssignmentChanges: boolean
  audienceAccessPreview?: AudienceAccessPreview
  onAssignmentDraftChange: (ids: number[]) => void
  onSaveAssignmentDraft: () => void
  onDiscardAssignmentDraft: () => void
  isAssigningCompanies: boolean
  onRemoveCompany: (companyId: number) => void
  isRemovingCompany: boolean
  onSaveTags: (tags: string[]) => void
  isSavingTags: boolean
  reviewHistoryItems: ReviewRequest[]
}

export function DocumentDetailsView({
  document,
  isEditor,
  showCompanySelector,
  onToggleCompanySelector,
  assignedCompanies,
  assignmentDraftIds,
  hasUnsavedAssignmentChanges,
  audienceAccessPreview,
  onAssignmentDraftChange,
  onSaveAssignmentDraft,
  onDiscardAssignmentDraft,
  isAssigningCompanies,
  onRemoveCompany,
  isRemovingCompany,
  onSaveTags,
  isSavingTags,
  reviewHistoryItems,
}: DocumentDetailsViewProps) {
  const showAssignmentSection =
    document.visibility === 'company' || isEditor || assignedCompanies.length > 0
  const isOverdue = isOverdueDueDate(document.due_date)

  return (
    <div className="surface-card rounded-2xl p-6 space-y-6">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <p className="helper-copy font-medium uppercase tracking-wide">Status</p>
          <p className="mt-1">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                document.status === 'active'
                  ? 'bg-emerald-100 text-emerald-700'
                  : document.status === 'approved'
                    ? 'bg-sky-100 text-sky-700'
                    : document.status === 'draft'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-slate-100 text-slate-700'
              }`}
            >
              {document.status === 'active'
                ? 'Published'
                : document.status === 'approved'
                  ? 'Approved'
                  : document.status}
            </span>
          </p>
        </div>
        <div>
          <p className="helper-copy font-medium uppercase tracking-wide">Visibility</p>
          <div className="mt-1">
            <VisibilityBadge visibility={document.visibility} showLabel />
          </div>
        </div>
        <div>
          <p className="helper-copy font-medium uppercase tracking-wide">Category</p>
          <p className="body-copy mt-1 text-slate-900 dark:text-slate-100">{document.category || '-'}</p>
        </div>
        <div>
          <p className="helper-copy font-medium uppercase tracking-wide">Created</p>
          <p className="body-copy mt-1 text-slate-900 dark:text-slate-100">
            {formatDate(document.created_at)}
          </p>
        </div>
        <div>
          <p className="helper-copy font-medium uppercase tracking-wide">Updated</p>
          <p className="body-copy mt-1 text-slate-900 dark:text-slate-100">
            {formatDate(document.updated_at)}
          </p>
        </div>
        <div>
          <p className="helper-copy font-medium uppercase tracking-wide">Due Date</p>
          <div className="body-copy mt-1 flex flex-wrap items-center gap-2 text-slate-900 dark:text-slate-100">
            <span>{formatDueDate(document.due_date)}</span>
            {isOverdue ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                Overdue
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div>
        <p className="helper-copy font-medium uppercase tracking-wide">Description</p>
        <p className="body-copy mt-1 whitespace-pre-wrap text-slate-900 dark:text-slate-100">
          {document.description || 'No description'}
        </p>
      </div>

      {audienceAccessPreview ? (
        <div className="border-t border-slate-200 pt-6">
          <p className="section-title text-base">Audience Access Preview</p>
          <p className="body-copy mt-2">{audienceAccessPreview.access_summary}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-1 font-medium ${
                audienceAccessPreview.is_public
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {audienceAccessPreview.is_public ? 'Public users' : 'No public access'}
            </span>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-1 font-medium ${
                audienceAccessPreview.includes_internal_users
                  ? 'bg-sky-100 text-sky-700'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {audienceAccessPreview.includes_internal_users
                ? 'Internal users included'
                : 'No internal access'}
            </span>
            {audienceAccessPreview.target_companies.length > 0 ? (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-700">
                {audienceAccessPreview.target_companies.length} assigned{' '}
                {audienceAccessPreview.target_companies.length === 1 ? 'company' : 'companies'}
              </span>
            ) : null}
          </div>
          {audienceAccessPreview.target_companies.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {audienceAccessPreview.target_companies.map((company) => (
                <span
                  key={company.id}
                  className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
                >
                  <Building2 className="w-3 h-3" />
                  {company.name}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div>
        <p className="helper-copy font-medium uppercase tracking-wide">Tags</p>
        <div className="mt-2">
          <TagEditor
            tags={(document.tags || '')
              .split(',')
              .map((tag) => tag.trim())
              .filter(Boolean)}
            canEdit={isEditor}
            isSaving={isSavingTags}
            onSave={onSaveTags}
          />
        </div>
      </div>

      {showAssignmentSection ? (
        <div className="border-t border-slate-200 pt-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-slate-500" />
              <p className="section-title text-base">Company Assignments</p>
            </div>
            {isEditor ? (
              <button
                type="button"
                onClick={onToggleCompanySelector}
                className="btn-secondary table-action-btn"
              >
                {showCompanySelector ? 'Cancel' : 'Assign Companies'}
              </button>
            ) : null}
          </div>
          <p className="helper-copy mb-3">
            {document.visibility === 'company'
              ? 'Assigned companies currently have audience access.'
              : 'Pre-assign companies here, then switch visibility to Company to grant access.'}
          </p>

          {showCompanySelector ? (
            <div className="surface-muted mb-4 p-4">
              <p className="body-copy mb-3">Select companies to assign this document to:</p>
              <CompanySelector
                selectedIds={assignmentDraftIds}
                selectedCompanyOptions={assignedCompanies}
                onChange={onAssignmentDraftChange}
                placeholder="Update assigned companies..."
                disabled={isAssigningCompanies || isRemovingCompany}
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <p
                  className={`helper-copy ${
                    hasUnsavedAssignmentChanges ? 'text-amber-700' : 'text-slate-500'
                  }`}
                >
                  {hasUnsavedAssignmentChanges
                    ? 'You have unsaved assignment changes.'
                    : 'No assignment changes pending.'}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onDiscardAssignmentDraft}
                    disabled={!hasUnsavedAssignmentChanges || isAssigningCompanies}
                    className="btn-ghost table-action-btn disabled:opacity-50"
                  >
                    Discard
                  </button>
                  <button
                    type="button"
                    onClick={onSaveAssignmentDraft}
                    disabled={!hasUnsavedAssignmentChanges || isAssigningCompanies}
                    className="btn-primary table-action-btn disabled:opacity-50"
                  >
                    {isAssigningCompanies ? 'Saving...' : 'Save Assignments'}
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {assignedCompanies.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {assignedCompanies.map((company) => (
                <div
                  key={company.id}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1.5 text-sm text-amber-700"
                >
                  <Building2 className="w-4 h-4" />
                  <span>{company.name}</span>
                  {isEditor ? (
                    <button
                      type="button"
                      onClick={() => onRemoveCompany(company.id)}
                      className="btn-icon h-7 w-7 border-0 bg-transparent text-amber-700 hover:bg-amber-100 hover:text-amber-900"
                      disabled={isRemovingCompany || isAssigningCompanies || showCompanySelector}
                      aria-label={`Remove ${company.name}`}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="body-copy">
              No companies assigned yet. {isEditor ? 'Click "Assign Companies" to add.' : ''}
            </p>
          )}
        </div>
      ) : null}

      {reviewHistoryItems.length > 0 ? (
        <div className="border-t border-slate-200 pt-6">
          <div className="mb-4 flex items-center gap-2">
            <History className="w-5 h-5 text-slate-500" />
            <p className="section-title text-base">Review History</p>
          </div>
          <div className="space-y-3">
            {reviewHistoryItems.slice(0, 5).map((review) => (
              <div
                key={review.id}
                className={`rounded-xl border p-3 ${
                  review.status === 'approved'
                    ? 'border-emerald-200 bg-emerald-50'
                    : review.status === 'rejected'
                      ? 'border-rose-200 bg-rose-50'
                      : review.status === 'pending'
                        ? 'border-amber-200 bg-amber-50'
                        : 'border-slate-200 bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {review.status === 'approved' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                    ) : null}
                    {review.status === 'rejected' ? (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    ) : null}
                    {review.status === 'pending' ? (
                      <Clock className="w-4 h-4 text-amber-600" />
                    ) : null}
                    <span className="card-title text-sm capitalize">{review.status}</span>
                  </div>
                  <span className="helper-copy">
                    {new Date(review.submitted_at).toLocaleDateString()}
                  </span>
                </div>
                {review.submitter ? (
                  <p className="helper-copy mt-1">Submitted by {review.submitter.full_name}</p>
                ) : null}
                {review.reviewer ? (
                  <p className="helper-copy">Reviewed by {review.reviewer.full_name}</p>
                ) : null}
                {review.review_comments ? (
                  <p className="body-copy mt-2 italic">"{review.review_comments}"</p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
