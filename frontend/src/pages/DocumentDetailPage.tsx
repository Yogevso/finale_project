import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import type { DocumentUpdate, DocumentStatus, DocumentVisibility, Attachment } from '@/types'
const VersionsSection = lazy(() => import('@/components/VersionsSection'))
const AttachmentsSection = lazy(() => import('@/components/AttachmentsSection'))
const CommentsSection = lazy(() => import('@/components/CommentsSection'))
import EngagementBar from '@/components/EngagementBar'
import VisibilityBadge from '@/components/VisibilityBadge'
import CompanySelector from '@/components/CompanySelector'
import NotFoundState from '@/components/NotFoundState'
import { Building2, X, Send, Clock, CheckCircle, XCircle, History, Maximize2, Minimize2, Edit3, Save } from 'lucide-react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import mammoth from 'mammoth'

type TabType = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

// Type for inline comment anchor
interface PendingAnchor {
  text: string
  id: string
}

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isEditor, isManager } = useAuth()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('preview')
  const [scrollProgress, setScrollProgress] = useState<number>(0)
  const [pendingAnchor, setPendingAnchor] = useState<PendingAnchor | null>(null)
  const isFullscreen = location.search.includes('fullscreen=1') || location.pathname.endsWith('/fullscreen')
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  // Callback for DocumentPreview to report scroll progress
  const handleScrollProgress = useCallback((progress: number) => {
    setScrollProgress(progress)
  }, [])

  const { data: document, isLoading, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.getDocument(Number(id)),
    enabled: !!id,
  })

  // Fetch attachments to check if there's a primary document to preview
  const { data: attachments = [] } = useQuery({
    queryKey: ['attachments', id],
    queryFn: () => api.getAttachments(Number(id)),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: (data: DocumentUpdate) => api.updateDocument(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteDocument(Number(id)),
    onSuccess: () => {
      navigate('/documents')
    },
    onError: (error: any) => {
      console.error('Delete error:', error)
      alert(error?.response?.data?.detail || error?.message || 'Failed to delete document')
    },
  })

  // Company assignment state and mutations (for visibility='company' documents)
  const [showCompanySelector, setShowCompanySelector] = useState(false)

  const { data: assignedCompaniesData } = useQuery({
    queryKey: ['document-assigned-companies', id],
    queryFn: () => api.getAssignedCompanies(Number(id)),
    enabled: !!id && document?.visibility === 'company',
  })

  const assignCompaniesMutation = useMutation({
    mutationFn: (companyIds: number[]) => api.assignCompanies(Number(id), companyIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-assigned-companies', id] })
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      setShowCompanySelector(false)
    },
  })

  const removeCompanyMutation = useMutation({
    mutationFn: (companyId: number) => api.removeCompanyAssignment(Number(id), companyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-assigned-companies', id] })
      queryClient.invalidateQueries({ queryKey: ['document', id] })
    },
  })

  // Submit for review state and mutation
  const [showSubmitReview, setShowSubmitReview] = useState(false)
  const [submitMessage, setSubmitMessage] = useState('')

  const submitReviewMutation = useMutation({
    mutationFn: (message?: string) => api.submitForReview(Number(id), { message }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
      setShowSubmitReview(false)
      setSubmitMessage('')
    },
  })

  // Fetch review history
  const { data: reviewHistory } = useQuery({
    queryKey: ['document-reviews', id],
    queryFn: () => api.getDocumentReviewHistory(Number(id)),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600"></div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <NotFoundState
        title="Document Not Found"
        description="This document may not exist or you may not have access."
      />
    )
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate()
    }
  }

  const contentWidthClass = contentWidth === 'fluid' ? 'max-w-none' : 'max-w-5xl'
  const readingModeClass = contentWidth === 'reading' ? 'reading-mode' : ''

  return (
    <div className={`${isFullscreen ? 'min-h-screen bg-slate-50 px-6 md:px-10 lg:px-14 py-6' : ''}`}>
      {isFullscreen && (
        <div className="sticky top-0 z-30 -mx-6 md:-mx-10 lg:-mx-14 px-6 md:px-10 lg:px-14 py-3 bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg flex items-center justify-between gap-4">
          <button
            onClick={() => navigate(`/documents/${id}`)}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/15 rounded-lg hover:bg-white/25 transition-colors"
          >
            <Minimize2 className="w-4 h-4" />
            Exit Fullscreen
          </button>
          <div className="flex-1 text-center font-display font-semibold truncate">{document.title}</div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => applyWidth('reading')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                contentWidth === 'reading'
                  ? 'bg-white text-sky-900 border-white'
                  : 'bg-white/10 text-white border-white/30 hover:bg-white/20'
              }`}
              title="Reading width"
            >
              Reading width
            </button>
            <button
              onClick={() => applyWidth('fluid')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                contentWidth === 'fluid'
                  ? 'bg-white text-sky-900 border-white'
                  : 'bg-white/10 text-white border-white/30 hover:bg-white/20'
              }`}
              title="Full width"
            >
              Full width
            </button>
          </div>
        </div>
      )}

      <div className={`space-y-6 ${readingModeClass} ${isFullscreen ? `w-full ${contentWidthClass} mx-auto` : ''}`}>
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg overflow-hidden">
        <div className="px-6 py-5 md:px-8 md:py-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <button
              onClick={() => navigate('/documents')}
              className="text-sm text-sky-100/80 hover:text-white mb-2"
            >
              ← Back to Documents
            </button>
            <h1 className="text-2xl md:text-3xl font-display font-bold">{document.title}</h1>
            <p className="text-sky-100/80 mt-1">{document.document_number}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {/* Fullscreen View Button */}
            {!isFullscreen ? (
              <button
                onClick={() => navigate(`/documents/${id}/fullscreen`)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
                title="Open Fullscreen View"
              >
                <Maximize2 className="w-4 h-4" />
                Fullscreen
              </button>
            ) : (
              <button
                onClick={() => navigate(`/documents/${id}`)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
                title="Exit Fullscreen View"
              >
                <Minimize2 className="w-4 h-4" />
                Exit Fullscreen
              </button>
            )}
            
            {isEditor && (
              <>
                {/* Submit for Review button - only show for draft documents */}
                {document.status === 'draft' && (
                  <button
                    onClick={() => setShowSubmitReview(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white text-sky-900 hover:bg-slate-100 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                    Submit for Review
                  </button>
                )}
                {document.status === 'pending_review' && (
                  <span className="flex items-center gap-2 px-4 py-2 bg-amber-200/30 text-amber-100 rounded-lg">
                    <Clock className="w-4 h-4" />
                    Pending Review
                  </span>
                )}
                {document.status === 'approved' && (
                  <span className="flex items-center gap-2 px-4 py-2 bg-sky-200/30 text-sky-100 rounded-lg">
                    <CheckCircle className="w-4 h-4" />
                    Approved (Ready to Publish)
                  </span>
                )}
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
                >
                  {isEditing ? 'Cancel' : 'Edit'}
                </button>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-rose-500 text-white rounded-lg hover:bg-rose-600"
                >
                  Delete
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Engagement Bar */}
      <EngagementBar documentId={Number(id)} scrollProgress={activeTab === 'preview' ? scrollProgress : undefined} />

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-6">
          {(['preview', 'details', 'versions', 'attachments', 'comments'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                activeTab === tab
                  ? 'border-sky-600 text-sky-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab === 'preview' ? '📄 Preview' : tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'preview' && (
        <DocumentPreview
          documentId={Number(id)}
          attachments={attachments}
          documentTitle={document.title}
          onScrollProgress={handleScrollProgress}
          isEditor={isEditor}
          widthMode={contentWidth}
        />
      )}

      {activeTab === 'details' && (
        <>
          {isEditing ? (
              <EditForm
                document={document}
                onSave={(data) => updateMutation.mutate(data)}
                onCancel={() => setIsEditing(false)}
                isLoading={updateMutation.isPending}
                canEditVisibility={isManager}
              />
          ) : (
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
                  <p className="mt-1 text-slate-900">
                    {new Date(document.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="text-sm text-slate-500">Updated</label>
                  <p className="mt-1 text-slate-900">
                    {new Date(document.updated_at).toLocaleString()}
                  </p>
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
                    {document.tags.split(',').map((tag, i) => (
                      <span
                        key={i}
                        className="pill bg-slate-100 text-slate-700"
                      >
                        {tag.trim()}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Company Assignment Section - only for company visibility */}
              {document.visibility === 'company' && (
                <div className="border-t border-slate-200 pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-5 h-5 text-slate-500" />
                      <label className="text-sm font-medium text-slate-700">Assigned Companies</label>
                    </div>
                    {isEditor && (
                      <button
                        onClick={() => setShowCompanySelector(!showCompanySelector)}
                        className="text-sm text-sky-600 hover:text-sky-700"
                      >
                        {showCompanySelector ? 'Cancel' : 'Assign Companies'}
                      </button>
                    )}
                  </div>

                  {showCompanySelector && (
                    <div className="mb-4 p-4 bg-slate-50 rounded-xl">
                      <p className="text-sm text-slate-600 mb-3">Select companies to assign this document to:</p>
                      <CompanySelector
                        selectedIds={assignedCompaniesData?.companies?.map(c => c.id) || []}
                        onChange={(ids) => {
                          assignCompaniesMutation.mutate(ids)
                        }}
                      />
                      {assignCompaniesMutation.isPending && (
                        <p className="mt-2 text-sm text-slate-500">Saving...</p>
                      )}
                    </div>
                  )}

                  {assignedCompaniesData?.companies && assignedCompaniesData.companies.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {assignedCompaniesData.companies.map((company) => (
                        <div
                          key={company.id}
                          className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full text-sm"
                        >
                          <Building2 className="w-4 h-4" />
                          <span>{company.name}</span>
                          {isEditor && (
                            <button
                              onClick={() => removeCompanyMutation.mutate(company.id)}
                              className="ml-1 hover:text-amber-900"
                              disabled={removeCompanyMutation.isPending}
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

              {/* Review History Section */}
              {reviewHistory?.items && reviewHistory.items.length > 0 && (
                <div className="border-t border-slate-200 pt-6">
                  <div className="flex items-center gap-2 mb-4">
                    <History className="w-5 h-5 text-slate-500" />
                    <label className="text-sm font-medium text-slate-700">Review History</label>
                  </div>
                  <div className="space-y-3">
                    {reviewHistory.items.slice(0, 5).map((review) => (
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
                          <p className="text-xs text-slate-600">
                            Reviewed by {review.reviewer.full_name}
                          </p>
                        )}
                        {review.review_comments && (
                          <p className="text-sm text-slate-700 mt-2 italic">
                            "{review.review_comments}"
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'versions' && (
        <Suspense fallback={<div className="surface-card rounded-2xl p-6">Loading versions...</div>}>
          <VersionsSection documentId={Number(id)} isEditor={isEditor} />
        </Suspense>
      )}

      {activeTab === 'attachments' && (
        <Suspense fallback={<div className="surface-card rounded-2xl p-6">Loading attachments...</div>}>
          <AttachmentsSection documentId={Number(id)} isEditor={isEditor} />
        </Suspense>
      )}

      {activeTab === 'comments' && (
        <Suspense fallback={<div className="surface-card rounded-2xl p-6">Loading comments...</div>}>
          <CommentsSection documentId={Number(id)} pendingAnchor={pendingAnchor} onClearAnchor={() => setPendingAnchor(null)} />
        </Suspense>
      )}

      {/* Submit for Review Modal */}
      {showSubmitReview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-display font-semibold text-slate-900 mb-4">Submit for Review</h3>
            <p className="text-sm text-slate-600 mb-4">
              This will submit "{document.title}" for review. A manager or peer editor can approve or reject it.
              Publishing happens later as a separate step.
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Message (optional)
              </label>
              <textarea
                value={submitMessage}
                onChange={(e) => setSubmitMessage(e.target.value)}
                placeholder="Add a note for the reviewer..."
                rows={3}
                className="input-field"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSubmitReview(false)
                  setSubmitMessage('')
                }}
                disabled={submitReviewMutation.isPending}
                className="btn-ghost"
              >
                Cancel
              </button>
              <button
                onClick={() => submitReviewMutation.mutate(submitMessage || undefined)}
                disabled={submitReviewMutation.isPending}
                className="btn-primary flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                {submitReviewMutation.isPending ? 'Submitting...' : 'Submit'}
              </button>
            </div>
            {submitReviewMutation.isError && (
              <p className="mt-3 text-sm text-rose-600">
                {(submitReviewMutation.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail ||
                  'Error submitting for review. Please try again.'}
              </p>
            )}
          </div>
        </div>
      )}
      </div>
    </div>
  )
}

function EditForm({
  document,
  onSave,
  onCancel,
  isLoading,
  canEditVisibility,
}: {
  document: { title: string; description?: string | null; status: DocumentStatus; visibility: DocumentVisibility; category?: string | null; release_branch?: string | null; tags?: string | null }
  onSave: (data: DocumentUpdate) => void
  onCancel: () => void
  isLoading: boolean
  canEditVisibility: boolean
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
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
            onChange={(e) => setFormData({ ...formData, visibility: e.target.value as DocumentVisibility })}
            className="select-field disabled:opacity-60"
            disabled={!canEditVisibility}
          >
            <option value="internal">🏢 Internal (Staff only)</option>
            <option value="public">🌐 Public (Everyone)</option>
            <option value="company">🔒 Company (Assigned companies)</option>
          </select>
          {formData.visibility === 'company' && canEditVisibility && (
            <p className="text-xs text-amber-600 mt-1">
              💡 After saving, go to the Details tab to assign specific companies
            </p>
          )}
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
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary disabled:opacity-50"
        >
          {isLoading ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}
// Section type for editing
interface TocSection {
  id: string
  text: string
  level: number
  html: string
  index: number
}

// Section Edit Popup Component
function SectionEditPopup({ section, onClose, onSave }: { section: TocSection; onClose: () => void; onSave: (newHtml: string, submitForReview: boolean) => Promise<void> }) {
  const [isSaving, setIsSaving] = useState(false)
  const [submitForReview, setSubmitForReview] = useState(true)
  
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: section.html,
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[200px] p-4',
      },
    },
  })

  const handleSave = async () => {
    if (!editor) return
    setIsSaving(true)
    try {
      await onSave(editor.getHTML(), submitForReview)
      onClose()
    } catch (error) {
      console.error('Failed to save section:', error)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div className="flex items-center gap-3">
            <Edit3 className="w-5 h-5 text-white" />
            <h2 className="text-lg font-display font-semibold text-white">Edit Section: {section.text}</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toolbar */}
        {editor && (
          <div className="flex flex-wrap gap-1 p-2 border-b border-slate-200 bg-slate-50">
            <button onClick={() => editor.chain().focus().toggleBold().run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('bold') ? 'bg-slate-200' : ''}`} title="Bold"><strong>B</strong></button>
            <button onClick={() => editor.chain().focus().toggleItalic().run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('italic') ? 'bg-slate-200' : ''}`} title="Italic"><em>I</em></button>
            <button onClick={() => editor.chain().focus().toggleUnderline().run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('underline') ? 'bg-slate-200' : ''}`} title="Underline"><span className="underline">U</span></button>
            <div className="w-px bg-slate-300 mx-1" />
            <button onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('heading', { level: 2 }) ? 'bg-slate-200' : ''}`} title="Heading 2">H2</button>
            <button onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('heading', { level: 3 }) ? 'bg-slate-200' : ''}`} title="Heading 3">H3</button>
            <div className="w-px bg-slate-300 mx-1" />
            <button onClick={() => editor.chain().focus().toggleBulletList().run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('bulletList') ? 'bg-slate-200' : ''}`} title="Bullet List">• List</button>
            <button onClick={() => editor.chain().focus().toggleOrderedList().run()} className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('orderedList') ? 'bg-slate-200' : ''}`} title="Numbered List">1. List</button>
          </div>
        )}

        {/* Editor Content */}
        <div className="flex-1 overflow-auto bg-white">
          <EditorContent editor={editor} className="min-h-[300px]" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50">
          <div className="text-sm text-slate-600">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={submitForReview}
                onChange={(e) => setSubmitForReview(e.target.checked)}
                className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
              />
              <span className="flex items-center gap-2">
                <Send className="w-4 h-4" />
                Submit for review after saving
              </span>
            </label>
            <p className="text-xs text-slate-400 mt-1 ml-6">An admin/manager will review and approve your changes</p>
          </div>
          <div className="flex gap-3">
            <button onClick={onClose} className="btn-ghost">Cancel</button>
            <button onClick={handleSave} disabled={isSaving} className="btn-primary flex items-center gap-2 disabled:opacity-50">
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : (submitForReview ? 'Save & Submit for Review' : 'Save as Draft')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Document Preview Component
function DocumentPreview({
  documentId,
  attachments,
  documentTitle,
  onScrollProgress,
  isEditor,
  widthMode = 'reading',
}: {
  documentId: number
  attachments: Attachment[]
  documentTitle?: string
  onScrollProgress?: (progress: number) => void
  isEditor?: boolean
  widthMode?: ReadingWidth
}) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [sections, setSections] = useState<TocSection[]>([])
  const [activeHeading, setActiveHeading] = useState<string | null>(null)
  const [tocCollapsed, setTocCollapsed] = useState(false)
  const [selectionPopup, setSelectionPopup] = useState<{ show: boolean; x: number; y: number; text: string }>({ show: false, x: 0, y: 0, text: '' })
  const [editingSection, setEditingSection] = useState<TocSection | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  // Inline comment popup state
  const [commentPopup, setCommentPopup] = useState<{ show: boolean; x: number; y: number; text: string; anchorId: string }>({ show: false, x: 0, y: 0, text: '', anchorId: '' })
  const [commentText, setCommentText] = useState('')
  const [isPrivateComment, setIsPrivateComment] = useState(false)
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)
  
  // Comment mutation
  const createCommentMutation = useMutation({
    mutationFn: (data: { content: string; is_private?: boolean; anchor_text?: string; anchor_id?: string }) => 
      api.createComment(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', documentId] })
      setCommentPopup({ show: false, x: 0, y: 0, text: '', anchorId: '' })
      setCommentText('')
      setIsPrivateComment(false)
      setIsSubmittingComment(false)
    },
    onError: () => {
      setIsSubmittingComment(false)
    }
  })

  // Handle text selection for inline comments
  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    // Don't close popup if clicking inside the comment popup
    if ((e.target as HTMLElement).closest('.inline-comment-popup')) {
      return
    }
    
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      // Only hide selection popup if comment popup is not open
      if (!commentPopup.show) {
        setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
      }
      return
    }
    
    const selectedText = selection.toString().trim()
    if (selectedText.length >= 3) {
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      setSelectionPopup({
        show: true,
        x: rect.left + rect.width / 2,
        y: rect.top - 10,
        text: selectedText
      })
    } else {
      setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
    }
  }, [commentPopup.show])

  // Open the full comment form popup
  const handleOpenCommentForm = useCallback(() => {
    if (selectionPopup.text) {
      const anchorId = `anchor-${Date.now()}`
      setCommentPopup({
        show: true,
        x: selectionPopup.x,
        y: selectionPopup.y + 60,
        text: selectionPopup.text,
        anchorId
      })
      setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
    }
  }, [selectionPopup])

  // Submit the inline comment
  const handleSubmitComment = useCallback(() => {
    if (!commentText.trim()) return
    setIsSubmittingComment(true)
    createCommentMutation.mutate({
      content: commentText.trim(),
      is_private: isPrivateComment,
      anchor_text: commentPopup.text,
      anchor_id: commentPopup.anchorId
    })
  }, [commentText, isPrivateComment, commentPopup, createCommentMutation])

  // Close comment popup
  const handleCloseCommentPopup = useCallback(() => {
    setCommentPopup({ show: false, x: 0, y: 0, text: '', anchorId: '' })
    setCommentText('')
    setIsPrivateComment(false)
    window.getSelection()?.removeAllRanges()
  }, [])

  // Calculate scroll progress
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget
    const scrollTop = container.scrollTop
    const scrollHeight = container.scrollHeight - container.clientHeight
    
    if (scrollHeight > 0) {
      const progress = Math.min(100, Math.round((scrollTop / scrollHeight) * 100))
      onScrollProgress?.(progress)
    }
    
    // Update active heading based on scroll position
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6')
    let currentActive = null
    
    headings.forEach((heading) => {
      const rect = heading.getBoundingClientRect()
      const containerRect = container.getBoundingClientRect()
      if (rect.top <= containerRect.top + 100) {
        currentActive = heading.id
      }
    })
    
    if (currentActive && currentActive !== activeHeading) {
      setActiveHeading(currentActive)
    }
  }

  // Find previewable attachments (PDF, images, or Word docs)
  const previewableAttachments = attachments.filter(
    (a) => a.mime_type === 'application/pdf' || 
           a.mime_type.startsWith('image/') ||
           a.mime_type === 'application/msword' ||
           a.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  )

  const isWordDoc = (att: Attachment | null) => {
    if (!att) return false
    return att.mime_type === 'application/msword' || 
           att.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  }

  const isSyntheticUploadPlaceholder = (content?: string | null) => {
    if (!content) return false
    return content.trim().toLowerCase().startsWith('uploaded from file:')
  }

  const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

  const clearHighlights = (container: HTMLElement) => {
    container.querySelectorAll('mark.doc-highlight').forEach((mark) => {
      const parent = mark.parentNode
      if (!parent) return
      parent.replaceChild(document.createTextNode(mark.textContent || ''), mark)
      parent.normalize()
    })
  }

  const applyHighlights = useCallback(() => {
    const container = document.getElementById('document-content-area')
    if (!container) return

    clearHighlights(container)
    const term = searchTerm.trim()
    if (!term) return

    const regex = new RegExp(escapeRegExp(term), 'gi')
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT
        const parent = (node as Text).parentElement
        if (!parent) return NodeFilter.FILTER_REJECT
        if (parent.tagName === 'MARK') return NodeFilter.FILTER_REJECT
        return NodeFilter.FILTER_ACCEPT
      },
    })

    const textNodes: Text[] = []
    let current = walker.nextNode()
    while (current) {
      textNodes.push(current as Text)
      current = walker.nextNode()
    }

    textNodes.forEach((node) => {
      const text = node.nodeValue
      if (!text) return
      if (!regex.test(text)) return
      regex.lastIndex = 0

      const fragment = document.createDocumentFragment()
      let lastIndex = 0
      let match
      while ((match = regex.exec(text)) !== null) {
        const start = match.index
        const end = start + match[0].length
        if (start > lastIndex) {
          fragment.appendChild(document.createTextNode(text.slice(lastIndex, start)))
        }
        const mark = document.createElement('mark')
        mark.className = 'doc-highlight'
        mark.textContent = text.slice(start, end)
        fragment.appendChild(mark)
        lastIndex = end
      }
      if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex)))
      }
      node.parentNode?.replaceChild(fragment, node)
    })
  }, [searchTerm])

  useEffect(() => {
    if (!htmlContent) return
    applyHighlights()
  }, [applyHighlights, htmlContent])

  // Extract headings from HTML content, add IDs, and create editable sections
  const processHtmlWithSections = useCallback((html: string) => {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const elements = Array.from(doc.body.children)
    const newSections: TocSection[] = []
    
    let currentSection: { heading: Element | null; content: Element[]; startIndex: number } = { heading: null, content: [], startIndex: 0 }
    
    elements.forEach((el, index) => {
      const tagName = el.tagName.toLowerCase()
      if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
        // Save previous section
        if (currentSection.heading || currentSection.content.length > 0) {
          const headingText = currentSection.heading?.textContent?.trim() || 'Introduction'
          const sectionId = `section-${newSections.length}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
          
          const sectionHtml = [
            currentSection.heading?.outerHTML || '',
            ...currentSection.content.map(c => c.outerHTML)
          ].join('\n')
          
          newSections.push({
            id: sectionId,
            text: headingText,
            level: currentSection.heading ? parseInt(currentSection.heading.tagName.charAt(1)) : 1,
            html: sectionHtml,
            index: newSections.length
          })
        }
        
        // Start new section
        el.setAttribute('id', `heading-${newSections.length}`)
        el.classList.add('scroll-mt-4')
        currentSection = { heading: el, content: [], startIndex: index }
      } else {
        currentSection.content.push(el)
      }
    })
    
    // Save last section
    if (currentSection.heading || currentSection.content.length > 0) {
      const headingText = currentSection.heading?.textContent?.trim() || 'Content'
      const sectionId = `section-${newSections.length}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
      
      const sectionHtml = [
        currentSection.heading?.outerHTML || '',
        ...currentSection.content.map(c => c.outerHTML)
      ].join('\n')
      
      newSections.push({
        id: sectionId,
        text: headingText,
        level: currentSection.heading ? parseInt(currentSection.heading.tagName.charAt(1)) : 1,
        html: sectionHtml,
        index: newSections.length
      })
    }
    
    setSections(newSections)
    return doc.body.innerHTML
  }, [])

  useEffect(() => {
    if (previewableAttachments.length > 0 && !selectedAttachment) {
      setSelectedAttachment(previewableAttachments[0])
    }
  }, [previewableAttachments, selectedAttachment])

  // State to track if we have inline content (no attachment needed)
  const [hasInlineContent, setHasInlineContent] = useState(false)

  useEffect(() => {
    const loadPreview = async () => {
      setIsLoading(true)
      setError(null)
      
      try {
        // First, check if there's a version with content (published preferred, else latest draft)
        const versionsResponse = await api.getVersions(documentId)
        const withContent = versionsResponse.items.filter(
          (v) => !!v.content?.trim() && !isSyntheticUploadPlaceholder(v.content)
        )
        const publishedVersion = withContent
          .filter(v => v.is_published)
          .sort((a, b) => new Date(b.published_at || b.created_at).getTime() - new Date(a.published_at || a.created_at).getTime())[0]
        const latestVersion = withContent
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
        let versionToShow = publishedVersion || latestVersion

        if (!versionToShow && versionsResponse.items.length > 0) {
          // Fallback: fetch latest version detail in case list response omits content
          const latest = versionsResponse.items[0]
          const fullVersion = await api.getVersion(documentId, latest.id)
          if (fullVersion?.content) {
            versionToShow = fullVersion
          }
        }

        if (versionToShow?.content) {
          // Use the latest available content (published if available)
          const processedHtml = processHtmlWithSections(versionToShow.content)
          setHtmlContent(processedHtml)
          setPreviewUrl(null)
          setHasInlineContent(true)
          setIsLoading(false)
          return
        }
        
        // No published version, fall back to attachment-based preview
        setHasInlineContent(false)
        
        if (!selectedAttachment) {
          setPreviewUrl(null)
          setHtmlContent(null)
          setSections([])
          setIsLoading(false)
          return
        }
        
        // No published version found, try to load from attachment
        if (isWordDoc(selectedAttachment)) {
          // Convert Word doc to HTML using mammoth (fallback if no version)
          const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
          const arrayBuffer = await blob.arrayBuffer()
          const result = await mammoth.convertToHtml({ arrayBuffer })
          const processedHtml = processHtmlWithSections(result.value)
          setHtmlContent(processedHtml)
          setPreviewUrl(null)
        } else if (selectedAttachment.mime_type === 'application/pdf') {
          // Show PDF preview directly from attachment if no version exists
          const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
          const url = URL.createObjectURL(blob)
          setPreviewUrl(url)
          setHtmlContent(null)
        } else {
          // For images and other files, create object URL for display
          const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
          const url = URL.createObjectURL(blob)
          setPreviewUrl(url)
          setHtmlContent(null)
          setSections([])
        }
      } catch (e) {
        console.error('Preview load error:', e)
        setError('Failed to load preview')
        setPreviewUrl(null)
        setHtmlContent(null)
        setSections([])
      } finally {
        setIsLoading(false)
      }
    }

    loadPreview()

    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [selectedAttachment, documentId])

  // Show content if we have inline content OR attachments
  if (attachments.length === 0 && !hasInlineContent && !htmlContent) {
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">📄</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No Content Yet</h3>
        <p className="text-slate-500">This document has no content. Add content using the editor or upload a file.</p>
      </div>
    )
  }

  if (!htmlContent && previewableAttachments.length === 0) {
    const firstAttachment = attachments[0]
    
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">📎</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">Preview Not Available</h3>
        <p className="text-slate-500 mb-4">
          This document type cannot be previewed.
          <br />
          Download the file to view it.
        </p>
        {firstAttachment && (
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/documents/${documentId}/attachments/${firstAttachment.id}/download`}
            download={firstAttachment.filename}
            onClick={async (e) => {
              e.preventDefault()
              try {
                const blob = await api.getAttachmentBlob(documentId, firstAttachment.id)
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = firstAttachment.filename
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                URL.revokeObjectURL(url)
              } catch (err) {
                console.error('Download failed:', err)
              }
            }}
            className="btn-primary inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download {firstAttachment.filename}
          </a>
        )}
      </div>
    )
  }

  const documentPaperClass =
    widthMode === 'fluid' ? 'document-preview-paper document-preview-paper-fluid' : 'document-preview-paper'

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      {/* Attachment selector if multiple */}
      {previewableAttachments.length > 1 && (
        <div className="border-b border-slate-200 p-3 bg-slate-50">
          <select
            value={selectedAttachment?.id || ''}
            onChange={(e) => {
              const att = previewableAttachments.find((a) => a.id === Number(e.target.value))
              setSelectedAttachment(att || null)
            }}
            className="select-field text-sm"
          >
            {previewableAttachments.map((att) => (
              <option key={att.id} value={att.id}>
                {att.filename} {isWordDoc(att) ? '(Word)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Preview area */}
      <div className="relative" style={{ minHeight: '600px' }}>
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2">⚠️</div>
              <p className="text-rose-600">{error}</p>
            </div>
          </div>
        ) : isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600"></div>
          </div>
        ) : htmlContent ? (
          // Word document rendered as HTML (read-only) with TOC sidebar
          <div className="flex h-[70vh]">
            {/* Table of Contents Sidebar */}
            {sections.length > 0 && (
              <div className={`bg-slate-50 border-r border-slate-200 transition-all duration-300 ${tocCollapsed ? 'w-10' : 'w-64'} flex-shrink-0`}>
                <div className="sticky top-0">
                  {/* TOC Header */}
                  <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-white">
                    {!tocCollapsed && (
                      <h3 className="font-medium text-sm text-slate-700 flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                        Contents
                      </h3>
                    )}
                    <button
                      onClick={() => setTocCollapsed(!tocCollapsed)}
                      className="p-1 hover:bg-slate-200 rounded text-slate-500"
                      title={tocCollapsed ? 'Expand' : 'Collapse'}
                    >
                      <svg className={`w-4 h-4 transition-transform ${tocCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                      </svg>
                    </button>
                  </div>
                  
                  {/* TOC Items with Edit buttons */}
                  {!tocCollapsed && (
                    <nav className="p-2 overflow-y-auto" style={{ maxHeight: 'calc(70vh - 50px)' }}>
                      <ul className="space-y-1">
                        {sections.map((item) => (
                          <li key={item.id} className="group">
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => {
                                  const element = document.getElementById(`heading-${item.index}`)
                                  if (element) {
                                    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                    setActiveHeading(item.id)
                                  }
                                }}
                                className={`flex-1 text-left px-2 py-1.5 text-sm rounded-l transition-colors hover:bg-sky-50 hover:text-sky-700 ${
                                  activeHeading === item.id ? 'bg-sky-100 text-sky-700 font-medium' : 'text-slate-600'
                                }`}
                                style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                              >
                                <span className="flex items-center gap-2">
                                  {item.level === 1 && <span className="text-sky-500">●</span>}
                                  {item.level === 2 && <span className="text-slate-400">○</span>}
                                  {item.level >= 3 && <span className="text-slate-300">-</span>}
                                  <span className="truncate">{item.text}</span>
                                </span>
                              </button>
                              {isEditor && (
                                <button
                                  onClick={() => setEditingSection(item)}
                                  className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-sky-100 rounded text-sky-600 transition-opacity"
                                  title="Edit section"
                                >
                                  <Edit3 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </nav>
                  )}
                </div>
              </div>
            )}

            {/* Document Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Document header bar */}
              <div className="bg-gradient-to-r from-sky-600 to-sky-700 text-white px-4 py-2 flex flex-col gap-2 md:flex-row md:items-center md:justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                  </svg>
                  <span className="font-medium truncate">{documentTitle || selectedAttachment?.filename}</span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search in document"
                      className="w-44 md:w-56 rounded-lg bg-white/15 text-white placeholder:text-white/70 border border-white/20 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-white/40"
                    />
                  </div>
                  {sections.length > 0 && (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded">
                      {sections.length} sections
                    </span>
                  )}
                  {isEditor ? (
                    <span className="text-xs bg-emerald-500/80 px-2 py-0.5 rounded whitespace-nowrap">Click section to edit</span>
                  ) : (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">Read Only</span>
                  )}
                </div>
              </div>
              
              {/* Document content with text selection for inline comments */}
              <div className="flex-1 relative overflow-auto document-preview-pane" onScroll={handleScroll}>
                <div className={documentPaperClass}>
                  <div 
                    id="document-content-area"
                    className="document-preview-content"
                    dangerouslySetInnerHTML={{ __html: htmlContent }}
                    onMouseUp={handleMouseUp}
                  />
                </div>
                
                {/* Text selection popup for adding inline comment */}
                {selectionPopup.show && !commentPopup.show && (
                  <div
                    className="fixed z-50 transform -translate-x-1/2 -translate-y-full"
                    style={{ left: selectionPopup.x, top: selectionPopup.y }}
                  >
                    <button
                      onClick={handleOpenCommentForm}
                      className="flex items-center gap-1 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full shadow-lg hover:bg-amber-600 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      Add Comment
                    </button>
                    <div className="absolute left-1/2 transform -translate-x-1/2 top-full">
                      <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-amber-500"></div>
                    </div>
                  </div>
                )}
                
                {/* Full inline comment form popup */}
                {commentPopup.show && user && (
                  <div
                    className="inline-comment-popup fixed z-50 transform -translate-x-1/2"
                    style={{ left: Math.max(180, Math.min(commentPopup.x, window.innerWidth - 180)), top: commentPopup.y }}
                  >
                    <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-80 overflow-hidden">
                      {/* Header with quoted text */}
                      <div className="bg-amber-50 border-b border-amber-100 px-4 py-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-amber-800 mb-1">Commenting on:</p>
                            <p className="text-sm text-amber-700 italic line-clamp-2">"{commentPopup.text.slice(0, 100)}{commentPopup.text.length > 100 ? '...' : ''}"</p>
                          </div>
                          <button
                            onClick={handleCloseCommentPopup}
                            className="p-1 hover:bg-amber-100 rounded text-amber-600"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      
                      {/* Comment form */}
                      <div className="p-4 space-y-3">
                        <textarea
                          value={commentText}
                          onChange={(e) => setCommentText(e.target.value)}
                          placeholder="Write your comment..."
                          className="input-field resize-none"
                          rows={3}
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                              handleSubmitComment()
                            }
                            if (e.key === 'Escape') {
                              handleCloseCommentPopup()
                            }
                          }}
                        />
                        
                        <div className="flex items-center justify-between">
                          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isPrivateComment}
                              onChange={(e) => setIsPrivateComment(e.target.checked)}
                              className="rounded border-slate-300 text-amber-500 focus:ring-amber-500"
                            />
                            <span className="flex items-center gap-1">
                              🔒 Private
                            </span>
                          </label>
                          
                          <div className="flex items-center gap-2">
                            <button
                              onClick={handleCloseCommentPopup}
                              className="btn-ghost text-sm"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleSubmitComment}
                              disabled={!commentText.trim() || isSubmittingComment}
                              className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                            >
                              {isSubmittingComment ? (
                                <>
                                  <span className="animate-spin">⏳</span>
                                  Posting...
                                </>
                              ) : (
                                <>
                                  <Send className="w-3.5 h-3.5" />
                                  Post
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                        
                        <p className="text-xs text-slate-400 text-center">
                          Press Ctrl+Enter to submit • Esc to cancel
                        </p>
                      </div>
                    </div>
                    {/* Arrow pointing up */}
                    <div className="absolute left-1/2 transform -translate-x-1/2 -top-2">
                      <div className="w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-white"></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : previewUrl && selectedAttachment?.mime_type === 'application/pdf' ? (
          <iframe
            src={previewUrl}
            className="w-full h-full absolute inset-0"
            style={{ minHeight: '600px' }}
            title="Document Preview"
          />
        ) : previewUrl && selectedAttachment?.mime_type.startsWith('image/') ? (
          <div className="p-4 flex items-center justify-center">
            <img
              src={previewUrl}
              alt={selectedAttachment.filename}
              className="max-w-full max-h-[600px] object-contain"
            />
          </div>
        ) : null}
      </div>

      {/* Download button */}
      {selectedAttachment && (
        <div className="border-t border-slate-200 p-3 bg-slate-50 flex justify-between items-center">
          <span className="text-sm text-slate-600">
            {documentTitle || selectedAttachment.filename}
            {isWordDoc(selectedAttachment) && (
              <span className="ml-2 text-xs text-sky-600">(Converted from Word)</span>
            )}
          </span>
          <a
            href={api.getAttachmentDownloadUrl(documentId, selectedAttachment.id)}
            download
            onClick={async (e) => {
              e.preventDefault()
              try {
                const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                // Use document title for download filename, keeping original extension
                const extension = selectedAttachment.filename.split('.').pop() || 'docx'
                const downloadName = documentTitle ? `${documentTitle}.${extension}` : selectedAttachment.filename
                a.download = downloadName
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                URL.revokeObjectURL(url)
              } catch (err) {
                console.error('Download failed:', err)
              }
            }}
            className="btn-primary text-sm"
          >
            Download Original
          </a>
        </div>
      )}

      {/* Section Edit Popup */}
      {editingSection && (
        <SectionEditPopup
          section={editingSection}
          onClose={() => setEditingSection(null)}
          onSave={async (newHtml, submitForReview) => {
            // Get old section content for comparison
            const oldSectionHtml = editingSection.html
            
            // Update the section in the sections array
            const updatedSections = sections.map((s, idx) => 
              idx === editingSection.index ? { ...s, html: newHtml } : s
            )
            
            // Rebuild full HTML from sections
            const newFullHtml = updatedSections.map(s => s.html).join('\n')
            
            // Update local state
            setHtmlContent(processHtmlWithSections(newFullHtml))
            
            // Create detailed change summary
            const changesSummary = `Section edited: "${editingSection.text}"\n\n` +
              `--- Original content ---\n${oldSectionHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${oldSectionHtml.length > 500 ? '...' : ''}\n\n` +
              `--- New content ---\n${newHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${newHtml.length > 500 ? '...' : ''}`
            
            // Save as new version (draft)
            const version = await api.createVersion(documentId, {
              content: newFullHtml,
              changes_summary: changesSummary,
            })
            
            // Set document status back to draft so it requires approval
            await api.updateDocument(documentId, { status: 'draft' as any })
            
            // If submitForReview is checked, auto-submit for review
            if (submitForReview) {
              await api.submitForReview(documentId, {
                version_id: version.id,
                message: `Edited section: "${editingSection.text}"`,
              })
            }
            
            queryClient.invalidateQueries({ queryKey: ['versions', documentId] })
            queryClient.invalidateQueries({ queryKey: ['document', documentId.toString()] })
            queryClient.invalidateQueries({ queryKey: ['reviews'] })
          }}
        />
      )}
    </div>
  )
}
