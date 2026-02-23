import CompanySelector from '@/components/CompanySelector'
import VisibilityBadge from '@/components/VisibilityBadge'
import type { Company, Document, ReviewRequest } from '@/types'
import { Building2, CheckCircle, Clock, History, X, XCircle } from 'lucide-react'

interface DocumentDetailsViewProps {
  document: Document
  isEditor: boolean
  showCompanySelector: boolean
  onToggleCompanySelector: () => void
  assignedCompanies: Company[]
  onAssignCompanies: (ids: number[]) => void
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
  onAssignCompanies,
  isAssigningCompanies,
  onRemoveCompany,
  isRemovingCompany,
  reviewHistoryItems,
}: DocumentDetailsViewProps) {
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
          <p className="mt-1 text-slate-900">{new Date(document.created_at).toLocaleString()}</p>
        </div>
        <div>
          <label className="text-sm text-slate-500">Updated</label>
          <p className="mt-1 text-slate-900">{new Date(document.updated_at).toLocaleString()}</p>
        </div>
      </div>

      <div>
        <label className="text-sm text-slate-500">Description</label>
        <p className="mt-1 text-slate-900 whitespace-pre-wrap">
          {document.description || 'No description'}
        </p>
      </div>

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

      {document.visibility === 'company' && (
        <div className="border-t border-slate-200 pt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-slate-500" />
              <label className="text-sm font-medium text-slate-700">Assigned Companies</label>
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

          {showCompanySelector && (
            <div className="mb-4 p-4 bg-slate-50 rounded-xl">
              <p className="text-sm text-slate-600 mb-3">
                Select companies to assign this document to:
              </p>
              <CompanySelector
                selectedIds={assignedCompanies.map((company) => company.id)}
                onChange={onAssignCompanies}
              />
              {isAssigningCompanies && <p className="mt-2 text-sm text-slate-500">Saving...</p>}
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
                      disabled={isRemovingCompany}
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
