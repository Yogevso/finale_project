import CompanySelector from '@/components/CompanySelector'
import VisibilityBadge from '@/components/VisibilityBadge'
import { formatDate } from '@/lib/dateUtils'
import type { AudienceAccessPreview, Company, Document, ReviewRequest } from '@/types'
import { Building2, CheckCircle, Clock, History, X, XCircle } from 'lucide-react'

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
  reviewHistoryItems,
}: DocumentDetailsViewProps) {
  const showAssignmentSection =
    document.visibility === 'company' || isEditor || assignedCompanies.length > 0

  return (
    <div className="surface-card rounded-2xl p-6 space-y-6">
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="text-sm text-slate-500">Status</label>
          <p className="mt-1">
            <span
              className={`px-2 py-1 text-xs rounded-full ${
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
          <label className="text-sm text-slate-500">Visibility</label>
          <div className="mt-1">
            <VisibilityBadge visibility={document.visibility} showLabel />
          </div>
        </div>
        <div>
          <label className="text-sm text-slate-500">Category</label>
          <p className="mt-1 text-slate-900">{document.category || '-'}</p>
        </div>
        <div>
          <label className="text-sm text-slate-500">Created</label>
          <p className="mt-1 text-slate-900">{formatDate(document.created_at)}</p>
        </div>
        <div>
          <label className="text-sm text-slate-500">Updated</label>
          <p className="mt-1 text-slate-900">{formatDate(document.updated_at)}</p>
        </div>
      </div>

      <div>
        <label className="text-sm text-slate-500">Description</label>
        <p className="mt-1 text-slate-900 whitespace-pre-wrap">
          {document.description || 'No description'}
        </p>
      </div>

      {audienceAccessPreview && (
        <div className="border-t border-slate-200 pt-6">
          <label className="text-sm font-medium text-slate-700">Audience Access Preview</label>
          <p className="mt-2 text-sm text-slate-600">{audienceAccessPreview.access_summary}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span
              className={`px-2 py-1 rounded-full ${
                audienceAccessPreview.is_public
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {audienceAccessPreview.is_public ? 'Public users' : 'No public access'}
            </span>
            <span
              className={`px-2 py-1 rounded-full ${
                audienceAccessPreview.includes_internal_users
                  ? 'bg-sky-100 text-sky-700'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {audienceAccessPreview.includes_internal_users
                ? 'Internal users included'
                : 'No internal access'}
            </span>
            {audienceAccessPreview.target_companies.length > 0 && (
              <span className="px-2 py-1 rounded-full bg-amber-100 text-amber-700">
                {audienceAccessPreview.target_companies.length} assigned{' '}
                {audienceAccessPreview.target_companies.length === 1 ? 'company' : 'companies'}
              </span>
            )}
          </div>
          {audienceAccessPreview.target_companies.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {audienceAccessPreview.target_companies.map((company) => (
                <span
                  key={company.id}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-amber-50 text-amber-700 text-xs"
                >
                  <Building2 className="w-3 h-3" />
                  {company.name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {document.tags && (
        <div>
          <label className="text-sm text-slate-500">Tags</label>
          <div className="mt-1 flex flex-wrap gap-2">
            {document.tags.split(',').map((tag, index) => (
              <span key={index} className="pill bg-slate-100 text-slate-700">
                {tag.trim()}
              </span>
            ))}
          </div>
        </div>
      )}

      {showAssignmentSection && (
        <div className="border-t border-slate-200 pt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-slate-500" />
              <label className="text-sm font-medium text-slate-700">Company Assignments</label>
            </div>
            {isEditor && (
              <button
                onClick={onToggleCompanySelector}
                className="text-sm text-sky-600 hover:text-sky-700"
              >
                {showCompanySelector ? 'Cancel' : 'Assign Companies'}
              </button>
            )}
          </div>
          <p className="text-xs text-slate-500 mb-3">
            {document.visibility === 'company'
              ? 'Assigned companies currently have audience access.'
              : 'Pre-assign companies here, then switch visibility to Company to grant access.'}
          </p>

          {showCompanySelector && (
            <div className="mb-4 p-4 bg-slate-50 rounded-xl">
              <p className="text-sm text-slate-600 mb-3">
                Select companies to assign this document to:
              </p>
              <CompanySelector
                selectedIds={assignmentDraftIds}
                selectedCompanyOptions={assignedCompanies}
                onChange={onAssignmentDraftChange}
                placeholder="Update assigned companies..."
                disabled={isAssigningCompanies || isRemovingCompany}
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <p
                  className={`text-xs ${
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
                    className="btn-ghost disabled:opacity-50"
                  >
                    Discard
                  </button>
                  <button
                    type="button"
                    onClick={onSaveAssignmentDraft}
                    disabled={!hasUnsavedAssignmentChanges || isAssigningCompanies}
                    className="btn-primary disabled:opacity-50"
                  >
                    {isAssigningCompanies ? 'Saving...' : 'Save Assignments'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {assignedCompanies.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {assignedCompanies.map((company) => (
                <div
                  key={company.id}
                  className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full text-sm"
                >
                  <Building2 className="w-4 h-4" />
                  <span>{company.name}</span>
                  {isEditor && (
                    <button
                      onClick={() => onRemoveCompany(company.id)}
                      className="ml-1 hover:text-amber-900"
                      disabled={isRemovingCompany || isAssigningCompanies || showCompanySelector}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No companies assigned yet. {isEditor && 'Click "Assign Companies" to add.'}
            </p>
          )}
        </div>
      )}

      {reviewHistoryItems.length > 0 && (
        <div className="border-t border-slate-200 pt-6">
          <div className="flex items-center gap-2 mb-4">
            <History className="w-5 h-5 text-slate-500" />
            <label className="text-sm font-medium text-slate-700">Review History</label>
          </div>
          <div className="space-y-3">
            {reviewHistoryItems.slice(0, 5).map((review) => (
              <div
                key={review.id}
                className={`p-3 rounded-xl border ${
                  review.status === 'approved'
                    ? 'bg-emerald-50 border-emerald-200'
                    : review.status === 'rejected'
                      ? 'bg-rose-50 border-rose-200'
                      : review.status === 'pending'
                        ? 'bg-amber-50 border-amber-200'
                        : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {review.status === 'approved' && (
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                    )}
                    {review.status === 'rejected' && (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    )}
                    {review.status === 'pending' && (
                      <Clock className="w-4 h-4 text-amber-600" />
                    )}
                    <span className="text-sm font-medium capitalize">{review.status}</span>
                  </div>
                  <span className="text-xs text-slate-500">
                    {new Date(review.submitted_at).toLocaleDateString()}
                  </span>
                </div>
                {review.submitter && (
                  <p className="text-xs text-slate-600 mt-1">
                    Submitted by {review.submitter.full_name}
                  </p>
                )}
                {review.reviewer && (
                  <p className="text-xs text-slate-600">Reviewed by {review.reviewer.full_name}</p>
                )}
                {review.review_comments && (
                  <p className="text-sm text-slate-700 mt-2 italic">"{review.review_comments}"</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
