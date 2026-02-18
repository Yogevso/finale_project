import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useCallback, useMemo, lazy, Suspense, useRef } from 'react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { sanitizeHtmlForPreview } from '@/lib/htmlSanitizer'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import PdfPreviewPanel, { type PdfTocItem } from '@/components/PdfPreviewPanel'
import type {
  Attachment,
  AttachmentOutlineItem,
  AttachmentReaderViewResponse,
  DocumentStatus,
  DocumentUpdate,
  DocumentVisibility,
} from '@/types'
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

type TabType = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'
type PdfPreviewMode = 'original' | 'reader'

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
  const [contentEditRequestToken, setContentEditRequestToken] = useState(0)
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
  const { data: attachmentsData } = useQuery({
    queryKey: ['attachments', id],
    queryFn: () => api.getAttachments(Number(id)),
    enabled: !!id,
    refetchInterval: (query) => {
      const items = (query.state.data as Attachment[] | undefined) ?? []
      const hasPendingPreview = items.some(
        (attachment) =>
          attachment.preview_pdf_status === 'pending' ||
          attachment.preview_pdf_status === 'processing',
      )
      return hasPendingPreview ? 2500 : false
    },
  })
  const attachments = useMemo(() => attachmentsData ?? [], [attachmentsData])

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
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      console.error('Delete error:', error)
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to delete document')
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
                  onClick={() => {
                    if (activeTab === 'details') {
                      if (isEditing) {
                        setIsEditing(false)
                        return
                      }
                      setIsEditing(true)
                      return
                    }
                    setIsEditing(false)
                    setActiveTab('preview')
                    setContentEditRequestToken((prev) => prev + 1)
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
                >
                  {activeTab === 'details'
                    ? isEditing
                      ? 'Cancel Details'
                      : 'Edit Details'
                    : 'Edit Content'}
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
          contentEditRequestToken={contentEditRequestToken}
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
  anchorId?: string
  pageStart?: number
  pageEnd?: number | null
}

type SectionEditMode = 'edit' | 'insert' | 'full'

interface SectionEditTarget extends TocSection {
  editMode?: SectionEditMode
  insertAfterIndex?: number
  fromChooser?: boolean
}

function ContentEditChooserPopup({
  sections,
  onClose,
  onEditSection,
  onAddSection,
}: {
  sections: TocSection[]
  onClose: () => void
  onEditSection: (section: TocSection) => void
  onAddSection: (insertAfterIndex: number) => void
}) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div>
            <h2 className="text-lg font-display font-semibold text-white">Edit Content Options</h2>
            <p className="text-xs text-sky-100 mt-1">
              Choose whether to edit an existing section or insert a new one.
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-6 p-6 overflow-auto">
          <section className="space-y-3">
            <h3 className="font-display font-semibold text-slate-900">Edit Existing Section</h3>
            <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
              {sections.map((section, idx) => (
                <button
                  key={`${section.id}-edit-${idx}`}
                  type="button"
                  onClick={() => onEditSection(section)}
                  className="w-full text-left p-3 rounded-xl border border-slate-200 hover:border-sky-300 hover:bg-sky-50 transition-colors"
                >
                  <div className="text-xs uppercase tracking-widest text-slate-400">
                    Section {idx + 1}
                  </div>
                  <div className="text-sm font-medium text-slate-900 mt-1">{section.text}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="font-display font-semibold text-slate-900">Add New Section</h3>
            <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
              {sections.length === 0 && (
                <button
                  type="button"
                  onClick={() => onAddSection(-1)}
                  className="w-full text-left p-3 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                >
                  <div className="text-sm font-medium text-emerald-800">Add first section</div>
                </button>
              )}

              {sections.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => onAddSection(-1)}
                    className="w-full text-left p-3 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                  >
                    <div className="text-xs uppercase tracking-widest text-emerald-700">Insert</div>
                    <div className="text-sm font-medium text-emerald-800 mt-1">
                      Before "{sections[0]?.text}"
                    </div>
                  </button>

                  {sections.map((section, idx) => {
                    const nextSection = sections[idx + 1]
                    const label = nextSection
                      ? `Between "${section.text}" and "${nextSection.text}"`
                      : `After "${section.text}"`
                    return (
                      <button
                        key={`${section.id}-insert-${idx}`}
                        type="button"
                        onClick={() => onAddSection(idx)}
                        className="w-full text-left p-3 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                      >
                        <div className="text-xs uppercase tracking-widest text-emerald-700">Insert</div>
                        <div className="text-sm font-medium text-emerald-800 mt-1">{label}</div>
                      </button>
                    )
                  })}
                </>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

// Section Edit Popup Component
function SectionEditPopup({
  section,
  onClose,
  onSave,
  onBack,
}: {
  section: SectionEditTarget
  onClose: () => void
  onSave: (newHtml: string, submitForReview: boolean) => Promise<void>
  onBack?: () => void
}) {
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

  const popupTitle =
    section.editMode === 'insert'
      ? 'Add New Section'
      : section.editMode === 'full'
        ? 'Edit Document Content'
        : `Edit Section: ${section.text}`

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div className="flex items-center gap-3">
            <Edit3 className="w-5 h-5 text-white" />
            <h2 className="text-lg font-display font-semibold text-white">{popupTitle}</h2>
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
            {onBack && (
              <button onClick={onBack} className="btn-ghost">
                Back
              </button>
            )}
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
  contentEditRequestToken = 0,
}: {
  documentId: number
  attachments: Attachment[]
  documentTitle?: string
  onScrollProgress?: (progress: number) => void
  isEditor?: boolean
  widthMode?: ReadingWidth
  contentEditRequestToken?: number
}) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [readerHtmlContent, setReaderHtmlContent] = useState<string | null>(null)
  const [readerStatus, setReaderStatus] = useState<AttachmentReaderViewResponse['status'] | null>(
    null,
  )
  const [readerError, setReaderError] = useState<string | null>(null)
  const [pdfPreviewMode, setPdfPreviewMode] = useState<PdfPreviewMode>('original')
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)
  const [pdfPreviewUnavailableError, setPdfPreviewUnavailableError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isReaderLoading, setIsReaderLoading] = useState(false)
  const [readerReloadToken, setReaderReloadToken] = useState(0)
  const [sections, setSections] = useState<TocSection[]>([])
  const [pdfOutlineSections, setPdfOutlineSections] = useState<TocSection[]>([])
  const [pdfOutlineLoading, setPdfOutlineLoading] = useState(false)
  const [pdfOutlineError, setPdfOutlineError] = useState<string | null>(null)
  const [pdfOutlinePage, setPdfOutlinePage] = useState<number | null>(null)
  const [readerCurrentPage, setReaderCurrentPage] = useState<number | null>(null)
  const [activeHeading, setActiveHeading] = useState<string | null>(null)
  const [tocCollapsed, setTocCollapsed] = useState(false)
  const [selectionPopup, setSelectionPopup] = useState<{ show: boolean; x: number; y: number; text: string }>({ show: false, x: 0, y: 0, text: '' })
  const [showContentEditChooser, setShowContentEditChooser] = useState(false)
  const [editingSection, setEditingSection] = useState<SectionEditTarget | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  // Inline comment popup state
  const [commentPopup, setCommentPopup] = useState<{ show: boolean; x: number; y: number; text: string; anchorId: string }>({ show: false, x: 0, y: 0, text: '', anchorId: '' })
  const [commentText, setCommentText] = useState('')
  const [isPrivateComment, setIsPrivateComment] = useState(false)
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)
  const [handledContentEditToken, setHandledContentEditToken] = useState(0)
  const previewPaneRef = useRef<HTMLDivElement | null>(null)
  const readerSyncNeededRef = useRef(false)
  
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
    const containerRect = container.getBoundingClientRect()
    
    if (scrollHeight > 0) {
      const progress = Math.min(100, Math.round((scrollTop / scrollHeight) * 100))
      onScrollProgress?.(progress)
    }

    if (showingReaderView) {
      const visiblePage = getVisibleReaderPage(container)
      if (visiblePage && visiblePage !== readerCurrentPage) {
        setReaderCurrentPage(visiblePage)
        setPdfOutlinePage((previous) => (previous === visiblePage ? previous : visiblePage))
      }
    }
    
    // Update active heading based on scroll position
    const headings = container.querySelectorAll(
      'h1[id], h2[id], h3[id], h4[id], h5[id], h6[id], section[id^="pdf-page-"]',
    )
    let currentActive = null
    
    headings.forEach((heading) => {
      const rect = heading.getBoundingClientRect()
      if (rect.top <= containerRect.top + 100) {
        currentActive = heading.id
      }
    })
    
    if (currentActive && currentActive !== activeHeading) {
      setActiveHeading(currentActive)
    }
  }

  // All attachments participate in preview-pdf pipeline.
  const previewableAttachments = useMemo(
    () => attachments,
    [attachments],
  )

  const isWordDoc = (att: Attachment | null) => {
    if (!att) return false
    return att.mime_type === 'application/msword' || 
           att.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  }

  const hasPreviewPdf = (att: Attachment | null) => {
    if (!att) return false
    if (att.preview_pdf_status === 'ready') return true
    return att.mime_type.startsWith('application/pdf')
  }

  const isPreviewPending = (att: Attachment | null) => {
    if (!att) return false
    return att.preview_pdf_status === 'pending' || att.preview_pdf_status === 'processing'
  }

  const isPreviewFailed = (att: Attachment | null) => {
    if (!att) return false
    return att.preview_pdf_status === 'failed'
  }

  const isSelectedPdf = hasPreviewPdf(selectedAttachment)
  const showingReaderView = isSelectedPdf && pdfPreviewMode === 'reader'
  const showingOriginalPdf = isSelectedPdf && pdfPreviewMode === 'original'
  const activeHtmlContent = showingReaderView ? readerHtmlContent : htmlContent
  const shouldRenderHtmlPreview = showingReaderView
    ? !!activeHtmlContent
    : !isSelectedPdf && !!activeHtmlContent

  const mapOutlineItemsToSections = useCallback((items: AttachmentOutlineItem[] = []): TocSection[] => {
    return items
      .map((item, index) => {
        const pageStart = item.page_start || item.page
        return {
          id: item.id || `toc-${index}`,
          text: item.title,
          level: Math.max(1, item.level || 1),
          html: '',
          index,
          anchorId: item.anchor_id || `pdf-page-${pageStart}`,
          pageStart,
          pageEnd: item.page_end ?? null,
        }
      })
      .filter((item) => item.text.trim().length > 0)
  }, [])

  const parsePageFromAnchorId = useCallback((anchorId?: string | null): number | null => {
    if (!anchorId) return null
    const pdfPageMatch = anchorId.match(/^pdf-page-(\d+)$/i)
    if (pdfPageMatch) {
      const parsed = Number(pdfPageMatch[1])
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null
    }
    const readerPageMatch = anchorId.match(/^reader-p(\d+)-/i)
    if (readerPageMatch) {
      const parsed = Number(readerPageMatch[1])
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null
    }
    return null
  }, [])

  const resolveSectionPageStart = useCallback(
    (item: TocSection): number | null => {
      const explicitPage = Number(item.pageStart || 0)
      if (Number.isFinite(explicitPage) && explicitPage > 0) {
        return explicitPage
      }
      return parsePageFromAnchorId(item.anchorId)
    },
    [parsePageFromAnchorId],
  )

  const getVisibleReaderPage = useCallback((container: HTMLElement): number | null => {
    const pageSections = Array.from(
      container.querySelectorAll<HTMLElement>('section.pdf-reader-page[data-page]'),
    )
    if (pageSections.length === 0) {
      return null
    }

    const containerRect = container.getBoundingClientRect()
    const thresholdTop = containerRect.top + 110
    let currentPage: number | null = null

    pageSections.forEach((section) => {
      const pageValue = Number(section.dataset.page || '')
      if (!Number.isFinite(pageValue) || pageValue <= 0) return
      const rect = section.getBoundingClientRect()
      if (rect.top <= thresholdTop) {
        currentPage = pageValue
      } else if (currentPage === null) {
        currentPage = pageValue
      }
    })

    return currentPage
  }, [])

  const navigateReaderToSection = useCallback(
    (item: TocSection, behavior: ScrollBehavior = 'smooth') => {
      const anchorId = item.anchorId || `heading-${item.index}`
      const pageStart = resolveSectionPageStart(item)
      const pageAnchorId = pageStart ? `pdf-page-${pageStart}` : null
      const targetElement =
        document.getElementById(anchorId) ||
        (pageAnchorId ? document.getElementById(pageAnchorId) : null)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior, block: 'start' })
      }

      if (pageStart) {
        setPdfOutlinePage(pageStart)
        setReaderCurrentPage(pageStart)
      }

      if (targetElement?.id) {
        setActiveHeading(targetElement.id)
      } else if (anchorId) {
        setActiveHeading(anchorId)
      }
    },
    [resolveSectionPageStart],
  )

  const isSyntheticUploadPlaceholder = (content?: string | null) => {
    if (!content) return false
    return content.trim().toLowerCase().startsWith('uploaded from file:')
  }

  const getUsableVersionContent = (content?: string | null): string | null => {
    if (!content) return null
    const trimmed = content.trim()
    if (!trimmed || isSyntheticUploadPlaceholder(trimmed)) {
      return null
    }
    return trimmed
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
    if (!activeHtmlContent) return
    applyHighlights()
  }, [activeHtmlContent, applyHighlights])

  // Extract headings from HTML content, add IDs, and create editable sections
  const processHtmlWithSections = useCallback((html: string) => {
    const sanitizedHtml = sanitizeHtmlForPreview(html)
    const parser = new DOMParser()
    const doc = parser.parseFromString(sanitizedHtml, 'text/html')
    const elements = Array.from(doc.body.children)
    const newSections: TocSection[] = []
    const allHeadingTags = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    const hasPrimaryHeadings = elements.some((element) => {
      const tagName = element.tagName.toLowerCase()
      return tagName === 'h1' || tagName === 'h2' || tagName === 'h3'
    })
    const tocHeadingTags = hasPrimaryHeadings
      ? new Set(['h1', 'h2', 'h3'])
      : allHeadingTags
    
    let currentSection: { heading: Element | null; content: Element[]; startIndex: number } = { heading: null, content: [], startIndex: 0 }
    
    elements.forEach((el, index) => {
      const tagName = el.tagName.toLowerCase()
      if (tocHeadingTags.has(tagName)) {
        // Save previous section
        if (currentSection.heading) {
          const headingText = currentSection.heading.textContent?.trim() || 'Section'
          const sectionId = `section-${newSections.length}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
          const headingAnchorId =
            currentSection.heading.getAttribute('id') || `heading-${newSections.length}`
          
          const sectionHtml = [
            currentSection.heading.outerHTML,
            ...currentSection.content.map(c => c.outerHTML)
          ].join('\n')
          
          newSections.push({
            id: sectionId,
            text: headingText,
            level: parseInt(currentSection.heading.tagName.charAt(1)),
            html: sectionHtml,
            index: newSections.length,
            anchorId: headingAnchorId,
          })
        }
        
        // Start new section
        const existingHeadingId = el.getAttribute('id')
        const headingAnchorId = existingHeadingId || `heading-${newSections.length}`
        el.setAttribute('id', headingAnchorId)
        el.classList.add('scroll-mt-4')
        currentSection = { heading: el, content: [], startIndex: index }
      } else if (currentSection.heading) {
        currentSection.content.push(el)
      }
    })
    
    // Save last section
    if (currentSection.heading) {
      const headingText = currentSection.heading.textContent?.trim() || 'Section'
      const sectionId = `section-${newSections.length}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
      const headingAnchorId =
        currentSection.heading.getAttribute('id') || `heading-${newSections.length}`
      
      const sectionHtml = [
        currentSection.heading.outerHTML,
        ...currentSection.content.map(c => c.outerHTML)
      ].join('\n')
      
      newSections.push({
        id: sectionId,
        text: headingText,
        level: parseInt(currentSection.heading.tagName.charAt(1)),
        html: sectionHtml,
        index: newSections.length,
        anchorId: headingAnchorId,
      })
    }

    if (newSections.length === 0) {
      const fullDocumentHtml = doc.body.innerHTML.trim()
      if (fullDocumentHtml) {
        newSections.push({
          id: 'section-0-full-document',
          text: 'Document Content',
          level: 1,
          html: fullDocumentHtml,
          index: 0,
          anchorId: 'document-content-area',
        })
      }
    }
    
    setSections(newSections)
    return doc.body.innerHTML
  }, [])

  useEffect(() => {
    if (previewableAttachments.length === 0 || selectedAttachment) return
    const preferred =
      previewableAttachments.find((att) => att.preview_pdf_status === 'ready') ||
      previewableAttachments.find((att) => att.mime_type.startsWith('application/pdf')) ||
      previewableAttachments[0]
    setSelectedAttachment(preferred)
  }, [previewableAttachments, selectedAttachment])

  useEffect(() => {
    if (!selectedAttachment) return
    const refreshed = previewableAttachments.find((att) => att.id === selectedAttachment.id)
    if (refreshed && refreshed !== selectedAttachment) {
      setSelectedAttachment(refreshed)
    }
  }, [previewableAttachments, selectedAttachment])

  useEffect(() => {
    if (!isSelectedPdf) {
      readerSyncNeededRef.current = false
      setPdfPreviewMode('original')
      setPdfPreviewUnavailableError(null)
      setReaderStatus(null)
      setReaderHtmlContent(null)
      setReaderError(null)
      setIsReaderLoading(false)
      setReaderReloadToken(0)
      setPdfOutlineSections([])
      setPdfOutlineLoading(false)
      setPdfOutlineError(null)
      setPdfOutlinePage(null)
      setReaderCurrentPage(null)
      setActiveHeading(null)
      return
    }

    readerSyncNeededRef.current = false
    setPdfPreviewMode('original')
    setPdfPreviewUnavailableError(null)
    setReaderStatus(selectedAttachment?.reader_html_status ?? null)
    setReaderHtmlContent(null)
    setReaderError(null)
    setIsReaderLoading(false)
    setReaderReloadToken(0)
    setPdfOutlinePage(null)
    setReaderCurrentPage(null)
    setActiveHeading(null)
  }, [isSelectedPdf, selectedAttachment?.id, selectedAttachment?.reader_html_status])

  // State to track if we have inline content (no attachment needed)
  const [hasInlineContent, setHasInlineContent] = useState(false)

  useEffect(() => {
    if (!isSelectedPdf || !selectedAttachment) {
      setPdfOutlineSections([])
      setPdfOutlineLoading(false)
      setPdfOutlineError(null)
      return
    }

    let cancelled = false
    setPdfOutlineLoading(true)
    setPdfOutlineError(null)

    api
      .getAttachmentOutline(documentId, selectedAttachment.id)
      .then((outlinePayload) => {
        if (cancelled) return
        const mappedSections = mapOutlineItemsToSections(outlinePayload.items || [])
        setPdfOutlineSections(mappedSections)
        if (mappedSections.length === 0) {
          setPdfOutlineError(outlinePayload.error || 'No TOC available')
        } else {
          setPdfOutlineError(outlinePayload.error || null)
        }
      })
      .catch((outlineError) => {
        if (cancelled) return
        console.error('Failed loading PDF TOC:', outlineError)
        setPdfOutlineSections([])
        setPdfOutlineError('Failed to load TOC')
      })
      .finally(() => {
        if (!cancelled) {
          setPdfOutlineLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [documentId, isSelectedPdf, mapOutlineItemsToSections, selectedAttachment])

  useEffect(() => {
    const loadPreview = async () => {
      setIsLoading(true)
      setError(null)
      
      try {
        if (previewableAttachments.length > 0) {
          if (!selectedAttachment) {
            const preferredAttachment =
              previewableAttachments.find((att) => att.preview_pdf_status === 'ready') ||
              previewableAttachments.find((att) => att.mime_type.startsWith('application/pdf')) ||
              previewableAttachments[0]
            if (preferredAttachment) {
              setSelectedAttachment(preferredAttachment)
              setIsLoading(false)
              return
            }
          }

          if (selectedAttachment && hasPreviewPdf(selectedAttachment)) {
            setHasInlineContent(false)
            setHtmlContent(null)
            setSections([])
            setPreviewUrl(api.getAttachmentPreviewUrl(documentId, selectedAttachment.id))
            setIsLoading(false)
            return
          }

          if (selectedAttachment && isPreviewPending(selectedAttachment)) {
            setHasInlineContent(false)
            setPreviewUrl(null)
            setHtmlContent(null)
            setSections([])
            setError(null)
            setIsLoading(false)
            return
          }

          if (selectedAttachment && isPreviewFailed(selectedAttachment)) {
            setHasInlineContent(false)
            setPreviewUrl(null)
            setHtmlContent(null)
            setSections([])
            setError(
              selectedAttachment.preview_pdf_error ||
                'Preview PDF generation failed for this attachment.',
            )
            setIsLoading(false)
            return
          }
        }

        // First, check if there's version content (published preferred, else latest draft)
        const versionsResponse = await api.getVersions(documentId)
        const withContent = versionsResponse.items.filter((v) => !!getUsableVersionContent(v.content))
        const publishedVersion = withContent
          .filter(v => v.is_published)
          .sort((a, b) => new Date(b.published_at || b.created_at).getTime() - new Date(a.published_at || a.created_at).getTime())[0]
        const latestVersion = withContent
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
        let versionToShow = publishedVersion || latestVersion

        if (!versionToShow && versionsResponse.items.length > 0) {
          // Fallback: list payload can omit/trim content; fetch details until a usable version is found.
          const prioritizedIds = [
            ...new Set([
              ...versionsResponse.items
                .filter((version) => version.is_published)
                .sort(
                  (a, b) =>
                    new Date(b.published_at || b.created_at).getTime() -
                    new Date(a.published_at || a.created_at).getTime(),
                )
                .map((version) => version.id),
              ...versionsResponse.items
                .sort(
                  (a, b) =>
                    new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
                )
                .map((version) => version.id),
            ]),
          ]

          for (const versionId of prioritizedIds) {
            const fullVersion = await api.getVersion(documentId, versionId)
            if (getUsableVersionContent(fullVersion?.content)) {
              versionToShow = fullVersion
              break
            }
          }
        }

        const versionContent = getUsableVersionContent(versionToShow?.content)
        if (versionContent) {
          // Created-in-app document fallback: no attachments available.
          const processedHtml = processHtmlWithSections(versionContent)
          setHtmlContent(processedHtml)
          setPreviewUrl(null)
          setHasInlineContent(true)
          setIsLoading(false)
          return
        }
        
        // No inline content and no ready preview artifact.
        setHasInlineContent(false)
        setPreviewUrl(null)
        setHtmlContent(null)
        setSections([])
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
      if (previewUrl?.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [documentId, previewableAttachments, processHtmlWithSections, selectedAttachment])

  useEffect(() => {
    if (!showingOriginalPdf || !previewUrl || !selectedAttachment) {
      setPdfPreviewUnavailableError(null)
    }
  }, [previewUrl, selectedAttachment, showingOriginalPdf])

  useEffect(() => {
    if (!showingReaderView || !selectedAttachment) return
    if (readerHtmlContent) return

    const attachmentId = selectedAttachment.id
    let cancelled = false
    let pollTimer: number | null = null

    const loadReaderArtifact = async (initialLoad: boolean) => {
      if (initialLoad) {
        setIsReaderLoading(true)
        setReaderError(null)
      }

      try {
        const readerView = await api.getAttachmentReaderView(documentId, attachmentId)
        if (cancelled) return

        setReaderStatus(readerView.status)
        const isReadyWithContent =
          readerView.status === 'ready' && !!readerView.html_content?.trim()

        if (isReadyWithContent) {
          const processedHtml = processHtmlWithSections(readerView.html_content || '')
          const mappedTocSections = mapOutlineItemsToSections(readerView.toc_items || [])
          setReaderHtmlContent(processedHtml)
          if (mappedTocSections.length > 0) {
            setSections(mappedTocSections)
            setPdfOutlineSections(mappedTocSections)
            setPdfOutlineError(null)
          }
          setReaderError(null)
          setReaderReloadToken(0)
          setIsReaderLoading(false)
          return
        }

        setReaderHtmlContent(null)

        const shouldFallbackToOriginal =
          readerView.status === 'failed' ||
          (readerView.status === 'ready' && !readerView.html_content?.trim())
        if (shouldFallbackToOriginal) {
          setReaderError(readerView.error || 'Reader View is unavailable for this PDF.')
          setPdfPreviewMode('original')
          setIsReaderLoading(false)
          return
        }

        setIsReaderLoading(false)
        pollTimer = window.setTimeout(() => {
          void loadReaderArtifact(false)
        }, 2000)
      } catch (loadError) {
        if (cancelled) return
        console.error('Reader View load error:', loadError)
        setReaderError('Failed to load Reader View. Showing original PDF.')
        setReaderHtmlContent(null)
        setPdfPreviewMode('original')
        setIsReaderLoading(false)
      }
    }

    void loadReaderArtifact(true)

    return () => {
      cancelled = true
      if (pollTimer !== null) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [
    documentId,
    mapOutlineItemsToSections,
    processHtmlWithSections,
    readerHtmlContent,
    readerReloadToken,
    selectedAttachment,
    showingReaderView,
  ])

  const handleRetryReaderView = useCallback(async () => {
    if (!selectedAttachment) return

    setIsReaderLoading(true)
    setReaderError(null)
    setReaderHtmlContent(null)
    setReaderStatus('pending')

    try {
      const payload = await api.retryAttachmentReaderView(documentId, selectedAttachment.id)
      setReaderStatus(payload.status)
      if (payload.status === 'ready' && payload.html_content?.trim()) {
        const processedHtml = processHtmlWithSections(payload.html_content)
        const mappedTocSections = mapOutlineItemsToSections(payload.toc_items || [])
        setReaderHtmlContent(processedHtml)
        if (mappedTocSections.length > 0) {
          setSections(mappedTocSections)
          setPdfOutlineSections(mappedTocSections)
          setPdfOutlineError(null)
        }
        setIsReaderLoading(false)
        return
      }
      setReaderReloadToken((prev) => prev + 1)
    } catch (retryError) {
      console.error('Reader View retry failed:', retryError)
      setReaderError('Retry failed. Showing original PDF.')
      setPdfPreviewMode('original')
      setIsReaderLoading(false)
    }
  }, [
    documentId,
    mapOutlineItemsToSections,
    processHtmlWithSections,
    selectedAttachment,
  ])

  const tocSectionsForHtml =
    showingReaderView && sections.length === 0 ? pdfOutlineSections : sections

  useEffect(() => {
    if (!showingReaderView || !activeHtmlContent) return
    if (!readerSyncNeededRef.current) return

    readerSyncNeededRef.current = false
    const pageFromActiveHeading = parsePageFromAnchorId(activeHeading)
    const fallbackTocPage =
      tocSectionsForHtml.length > 0 ? resolveSectionPageStart(tocSectionsForHtml[0]) : null
    const targetPage = pdfOutlinePage || pageFromActiveHeading || fallbackTocPage || null
    const targetAnchorId = activeHeading || (targetPage ? `pdf-page-${targetPage}` : null)

    const rafId = window.requestAnimationFrame(() => {
      const pane = previewPaneRef.current
      const targetElement =
        (targetAnchorId ? document.getElementById(targetAnchorId) : null) ||
        (targetPage ? document.getElementById(`pdf-page-${targetPage}`) : null)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'auto', block: 'start' })
        if (targetElement.id) {
          setActiveHeading(targetElement.id)
        }
      }

      const visiblePage = pane ? getVisibleReaderPage(pane) : null
      const resolvedPage = targetPage || visiblePage
      if (resolvedPage) {
        setReaderCurrentPage(resolvedPage)
        setPdfOutlinePage((previous) => (previous === resolvedPage ? previous : resolvedPage))
      }
    })

    return () => {
      window.cancelAnimationFrame(rafId)
    }
  }, [
    activeHeading,
    activeHtmlContent,
    getVisibleReaderPage,
    parsePageFromAnchorId,
    pdfOutlinePage,
    resolveSectionPageStart,
    showingReaderView,
    tocSectionsForHtml,
  ])

  useEffect(() => {
    if (!contentEditRequestToken || contentEditRequestToken === handledContentEditToken) {
      return
    }

    if (!isEditor) {
      setHandledContentEditToken(contentEditRequestToken)
      return
    }

    // Reader mode is non-editable; switch back to original first and continue on next render.
    if (showingReaderView) {
      setPdfPreviewMode('original')
      return
    }

    if (!activeHtmlContent || isLoading) {
      return
    }

    setEditingSection(null)
    setShowContentEditChooser(true)
    setHandledContentEditToken(contentEditRequestToken)
  }, [
    activeHtmlContent,
    contentEditRequestToken,
    handledContentEditToken,
    isEditor,
    isLoading,
    showingReaderView,
    tocSectionsForHtml,
  ])

  const handleSwitchToOriginalPdf = useCallback(() => {
    readerSyncNeededRef.current = false
    setPdfPreviewMode('original')
  }, [])

  const handleSwitchToReaderView = useCallback(() => {
    readerSyncNeededRef.current = true
    const fallbackPage =
      pdfOutlinePage ||
      readerCurrentPage ||
      parsePageFromAnchorId(activeHeading) ||
      (pdfOutlineSections.length > 0 ? resolveSectionPageStart(pdfOutlineSections[0]) : null)

    if (fallbackPage) {
      setPdfOutlinePage(fallbackPage)
      setReaderCurrentPage(fallbackPage)
      if (!activeHeading) {
        setActiveHeading(`pdf-page-${fallbackPage}`)
      }
    }
    setPdfPreviewMode('reader')
  }, [
    activeHeading,
    parsePageFromAnchorId,
    pdfOutlinePage,
    pdfOutlineSections,
    readerCurrentPage,
    resolveSectionPageStart,
  ])

  const handleReaderTocClick = useCallback(
    (item: TocSection) => {
      navigateReaderToSection(item, 'smooth')
    },
    [navigateReaderToSection],
  )

  const handlePdfTocClick = useCallback(
    (item: TocSection) => {
      const pageStart = resolveSectionPageStart(item)
      const anchorId = item.anchorId || (pageStart ? `pdf-page-${pageStart}` : `heading-${item.index}`)
      if (pageStart) {
        setPdfOutlinePage(pageStart)
        setReaderCurrentPage(pageStart)
      }
      setActiveHeading(anchorId)
    },
    [resolveSectionPageStart],
  )

  const handlePdfIframeError = useCallback(() => {
    setPdfPreviewUnavailableError('PDF preview unavailable. Please download original.')
  }, [])

  // Show content if we have inline content OR attachments
  if (attachments.length === 0 && !hasInlineContent && !activeHtmlContent) {
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">📄</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No Content Yet</h3>
        <p className="text-slate-500">This document has no content. Add content using the editor or upload a file.</p>
      </div>
    )
  }

  if (!activeHtmlContent && previewableAttachments.length === 0) {
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
  const effectivePdfPage = pdfOutlinePage || readerCurrentPage
  const pdfPreviewSrc = previewUrl && effectivePdfPage ? `${previewUrl}#page=${effectivePdfPage}` : previewUrl
  const pdfTocItems: PdfTocItem[] = pdfOutlineSections
    .map((item) => {
      const pageStart = resolveSectionPageStart(item)
      if (!pageStart) return null
      return {
        id: item.id,
        title: item.text,
        level: Math.max(1, item.level || 1),
        pageStart,
      }
    })
    .filter((item): item is PdfTocItem => item !== null)

  const handlePdfPreviewPanelSelect = (item: PdfTocItem) => {
    const matched = pdfOutlineSections.find((section) => section.id === item.id)
    if (matched) {
      handlePdfTocClick(matched)
      return
    }

    setPdfOutlinePage(item.pageStart)
    setReaderCurrentPage(item.pageStart)
    setActiveHeading(`pdf-page-${item.pageStart}`)
  }

  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      {(previewableAttachments.length > 1 || isSelectedPdf) && (
        <div className="border-b border-slate-200 p-3 bg-slate-50 flex flex-wrap items-center gap-3 justify-between">
          {previewableAttachments.length > 1 ? (
            <select
              value={selectedAttachment?.id || ''}
              onChange={(e) => {
                const att = previewableAttachments.find((a) => a.id === Number(e.target.value))
                setSelectedAttachment(att || null)
              }}
              className="select-field text-sm min-w-[220px] max-w-md"
            >
              {previewableAttachments.map((att) => (
                <option key={att.id} value={att.id}>
                  {att.filename} {isWordDoc(att) ? '(Word)' : ''}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm font-medium text-slate-600">{selectedAttachment?.filename}</span>
          )}

          {isSelectedPdf && (
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex rounded-xl border border-slate-300 bg-white p-1">
                <button
                  type="button"
                  onClick={handleSwitchToOriginalPdf}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    pdfPreviewMode === 'original'
                      ? 'bg-sky-600 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  View Original (PDF)
                </button>
                <button
                  type="button"
                  onClick={handleSwitchToReaderView}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    pdfPreviewMode === 'reader'
                      ? 'bg-sky-600 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  Reader View
                </button>
              </div>
              {showingReaderView && (readerStatus === 'pending' || readerStatus === 'processing') && (
                <span className="text-xs text-slate-500">Generating Reader View...</span>
              )}
              {readerError && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-amber-700">{readerError}</span>
                  {(readerStatus === 'failed' || readerStatus === 'ready') && (
                    <button
                      type="button"
                      onClick={handleRetryReaderView}
                      className="px-2 py-1 text-xs rounded-md border border-amber-300 text-amber-700 hover:bg-amber-50"
                    >
                      Retry
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
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
        ) : isLoading || (showingReaderView && isReaderLoading && !activeHtmlContent) ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600 mx-auto"></div>
              {showingReaderView && (
                <p className="text-xs text-slate-500 mt-3">Preparing Reader View...</p>
              )}
            </div>
          </div>
        ) : shouldRenderHtmlPreview ? (
          // Word document rendered as HTML (read-only) with TOC sidebar
          <div className="flex h-[70vh]">
            {/* Table of Contents Sidebar */}
            <div className={`bg-slate-50 border-r border-slate-200 transition-all duration-300 ${tocCollapsed ? 'w-10' : 'w-56'} flex-shrink-0`}>
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
                    {tocSectionsForHtml.length === 0 ? (
                      <p className="px-2 py-2 text-sm text-slate-500">No TOC available</p>
                    ) : (
                      <ul className="space-y-1">
                        {tocSectionsForHtml.map((item) => {
                          const anchorId = item.anchorId || `heading-${item.index}`
                          const pageStart = resolveSectionPageStart(item)
                          const isActiveItem =
                            activeHeading === anchorId ||
                            (!!pageStart && readerCurrentPage === pageStart)
                          return (
                            <li key={item.id} className="group">
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleReaderTocClick(item)}
                                  className={`flex-1 text-left px-2 py-1.5 text-sm rounded-l transition-colors hover:bg-sky-50 hover:text-sky-700 ${
                                    isActiveItem
                                      ? 'bg-sky-100 text-sky-700 font-medium'
                                      : 'text-slate-600'
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
                                {isEditor && !showingReaderView && (
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
                          )
                        })}
                      </ul>
                    )}
                  </nav>
                )}
              </div>
            </div>

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
                  {tocSectionsForHtml.length > 0 && (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded">
                      {tocSectionsForHtml.length} sections
                    </span>
                  )}
                  {showingReaderView && readerCurrentPage && (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
                      Page {readerCurrentPage}
                    </span>
                  )}
                  {isEditor && !showingReaderView ? (
                    <span className="text-xs bg-emerald-500/80 px-2 py-0.5 rounded whitespace-nowrap">Click section to edit</span>
                  ) : (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
                      {showingReaderView ? 'Reader View' : 'Read Only'}
                    </span>
                  )}
                </div>
              </div>
              
              {/* Document content with text selection for inline comments */}
              <div
                ref={previewPaneRef}
                className="flex-1 relative overflow-y-auto overflow-x-hidden document-preview-pane"
                onScroll={handleScroll}
              >
                <div className={documentPaperClass}>
                  <div 
                    id="document-content-area"
                    className={`document-preview-content ${showingReaderView ? 'document-preview-content--reader' : ''}`}
                    dangerouslySetInnerHTML={{ __html: activeHtmlContent || '' }}
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
        ) : showingReaderView ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">📄</div>
              <p className="text-slate-700 font-medium mb-1">Reader View is being generated</p>
              <p className="text-sm text-slate-500">
                The original PDF is available immediately. Switch back to
                <span className="font-medium text-slate-700"> View Original (PDF)</span> at any time.
              </p>
            </div>
          </div>
        ) : showingOriginalPdf && pdfPreviewUnavailableError ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">⚠️</div>
              <p className="text-rose-700 font-medium mb-1">
                PDF preview unavailable. Please download original.
              </p>
            </div>
          </div>
        ) : showingOriginalPdf && previewUrl ? (
          <PdfPreviewPanel
            tocItems={pdfTocItems}
            tocLoading={pdfOutlineLoading}
            tocError={pdfOutlineError}
            selectedPage={effectivePdfPage}
            onSelectItem={handlePdfPreviewPanelSelect}
            iframeSrc={pdfPreviewSrc}
            iframeKey={`${selectedAttachment?.id || 'preview'}-${effectivePdfPage || 'base'}`}
            iframeTitle="Document Preview"
            onIframeError={handlePdfIframeError}
          />
        ) : selectedAttachment && isPreviewPending(selectedAttachment) ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-600 mx-auto mb-3"></div>
              <p className="text-slate-700 font-medium mb-1">Generating PDF preview...</p>
              <p className="text-sm text-slate-500">
                The original file is preserved. Preview, TOC and Reader will appear once conversion finishes.
              </p>
            </div>
          </div>
        ) : selectedAttachment && isPreviewFailed(selectedAttachment) ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">⚠️</div>
              <p className="text-rose-700 font-medium mb-1">Preview PDF generation failed</p>
              <p className="text-sm text-rose-600">
                {selectedAttachment.preview_pdf_error || 'Could not build a PDF preview for this attachment.'}
              </p>
            </div>
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
          <div className="flex items-center gap-2">
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
                  const baseName = (documentTitle || selectedAttachment.filename || 'document').replace(
                    /\.[^/.]+$/,
                    '',
                  )
                  a.download = `${baseName}.pdf`
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
              Download PDF
            </a>
            <a
              href={api.getAttachmentOriginalDownloadUrl(documentId, selectedAttachment.id)}
              className="btn-secondary text-sm"
            >
              Download Original
            </a>
          </div>
        </div>
      )}

      {/* Content Edit Chooser Popup */}
      {showContentEditChooser && (
        <ContentEditChooserPopup
          sections={tocSectionsForHtml}
          onClose={() => setShowContentEditChooser(false)}
          onEditSection={(section) => {
            setShowContentEditChooser(false)
            setEditingSection({
              ...section,
              editMode: section.index < 0 ? 'full' : 'edit',
              fromChooser: true,
            })
          }}
          onAddSection={(insertAfterIndex) => {
            const neighbor =
              insertAfterIndex >= 0
                ? tocSectionsForHtml[insertAfterIndex]
                : tocSectionsForHtml[0]
            const headingLevel = Math.min(6, Math.max(2, neighbor?.level || 2))
            const headingTag = `h${headingLevel}`
            const defaultTitle = 'New Section'
            const defaultHtml = `<${headingTag}>${defaultTitle}</${headingTag}><p>Write section content here.</p>`

            setShowContentEditChooser(false)
            setEditingSection({
              id: `insert-${Date.now()}-${insertAfterIndex}`,
              text: defaultTitle,
              level: headingLevel,
              html: defaultHtml,
              index: Math.max(0, insertAfterIndex + 1),
              editMode: 'insert',
              insertAfterIndex,
              fromChooser: true,
            })
          }}
        />
      )}

      {/* Section Edit Popup */}
      {editingSection && (
        <SectionEditPopup
          section={editingSection}
          onClose={() => setEditingSection(null)}
          onBack={
            editingSection.fromChooser
              ? () => {
                  setEditingSection(null)
                  setShowContentEditChooser(true)
                }
              : undefined
          }
          onSave={async (newHtml, submitForReview) => {
            // Get old section content for comparison
            const oldSectionHtml = editingSection.editMode === 'insert' ? '' : editingSection.html

            let newFullHtml = ''
            if (editingSection.editMode === 'insert') {
              const insertAt = Math.max(
                0,
                Math.min(sections.length, (editingSection.insertAfterIndex ?? -1) + 1),
              )
              const updatedSections = [...sections]
              updatedSections.splice(insertAt, 0, {
                ...editingSection,
                html: newHtml,
                index: insertAt,
              })
              newFullHtml = updatedSections.map((s) => s.html).join('\n')
            } else if (editingSection.index < 0 || editingSection.editMode === 'full') {
              newFullHtml = newHtml
            } else {
              newFullHtml = sections
                .map((s, idx) => (idx === editingSection.index ? { ...s, html: newHtml } : s))
                .map((s) => s.html)
                .join('\n')
            }
            
            // Update local state
            setHtmlContent(processHtmlWithSections(newFullHtml))

            // Create detailed change summary
            const sectionAction = editingSection.editMode === 'insert' ? 'Section added' : 'Section edited'
            const oldContentSummary =
              editingSection.editMode === 'insert'
                ? 'N/A (new section)'
                : `${oldSectionHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${
                    oldSectionHtml.length > 500 ? '...' : ''
                  }`
            const changesSummary = `${sectionAction}: "${editingSection.text}"\n\n` +
              `--- Original content ---\n${oldContentSummary}\n\n` +
              `--- New content ---\n${newHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${
                newHtml.length > 500 ? '...' : ''
              }`
            
            // Save as new version (draft)
            const version = await api.createVersion(documentId, {
              content: newFullHtml,
              changes_summary: changesSummary,
            })
            
            // Set document status back to draft so it requires approval
            await api.updateDocument(documentId, { status: 'draft' })
            
            // If submitForReview is checked, auto-submit for review
            if (submitForReview) {
              const reviewActionLabel =
                editingSection.editMode === 'insert' ? 'Added section' : 'Edited section'
              await api.submitForReview(documentId, {
                version_id: version.id,
                message: `${reviewActionLabel}: "${editingSection.text}"`,
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
