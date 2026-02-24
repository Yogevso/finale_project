/**
 * CustomerDocumentPage - Document detail view for customer portal
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portalApi } from '../../lib/portalApi'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import FeedbackForm from '../../components/FeedbackForm'
import {
  FileText,
  ArrowLeft,
  Paperclip,
  Download,
  Tag,
  Folder,
  Clock,
  CheckCircle,
} from 'lucide-react'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import NotFoundState from '@/components/NotFoundState'

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function CustomerDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))
  const { isCustomer } = useAuth()
  const contentRef = useRef<HTMLDivElement | null>(null)
  const lastSavedProgress = useRef<number>(0)
  const rafId = useRef<number | null>(null)
  const isFullscreen = location.search.includes('fullscreen=1')

  // Fetch document
  const { data: document, isLoading, error } = useQuery({
    queryKey: ['portal', 'document', id],
    queryFn: () => portalApi.getDocument(Number(id)),
    enabled: !!id,
  })

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: (data: { feedback_type: 'question' | 'suggestion' | 'issue' | 'other'; content: string }) =>
      portalApi.submitFeedback({
        document_id: Number(id),
        ...data,
      }),
    onSuccess: () => {
      setFeedbackSubmitted(true)
      queryClient.invalidateQueries({ queryKey: ['portal', 'feedback'] })
    },
  })

  const updateProgressMutation = useMutation({
    mutationFn: (percent: number) => api.updateReadingProgress(Number(id), percent),
  })

  const computeAndSaveProgress = useCallback(() => {
    if (!isCustomer || !contentRef.current || !id) {
      return
    }

    const element = contentRef.current
    const scrollY = window.scrollY
    const elementTop = element.getBoundingClientRect().top + scrollY
    const elementHeight = element.scrollHeight
    const viewportHeight = window.innerHeight
    const end = elementTop + elementHeight - viewportHeight

    let progress = 0
    if (end <= elementTop) {
      progress = 100
    } else if (scrollY <= elementTop) {
      progress = 0
    } else if (scrollY >= end) {
      progress = 100
    } else {
      progress = Math.round(((scrollY - elementTop) / (end - elementTop)) * 100)
    }

    progress = Math.max(0, Math.min(100, progress))
    if (progress <= lastSavedProgress.current) {
      return
    }

    const currentMilestone = Math.floor(progress / 10) * 10
    const savedMilestone = Math.floor(lastSavedProgress.current / 10) * 10
    if (currentMilestone > savedMilestone && progress > lastSavedProgress.current) {
      lastSavedProgress.current = progress
      updateProgressMutation.mutate(progress)
    }
  }, [id, isCustomer, updateProgressMutation])

  useEffect(() => {
    if (!isCustomer || !id) {
      return
    }

    const handleScroll = () => {
      if (rafId.current !== null) {
        return
      }
      rafId.current = window.requestAnimationFrame(() => {
        rafId.current = null
        computeAndSaveProgress()
      })
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()

    return () => {
      window.removeEventListener('scroll', handleScroll)
      if (rafId.current !== null) {
        window.cancelAnimationFrame(rafId.current)
        rafId.current = null
      }
    }
  }, [computeAndSaveProgress, id, isCustomer])

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600"></div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="py-12">
        <NotFoundState
          title="Document Not Found"
          description="This document may not exist or you don't have access to view it."
          icon={<FileText className="h-12 w-12 text-slate-300" />}
          action={
            <Link
              to="/portal/documents"
              className="inline-flex items-center text-sky-600 hover:text-sky-500"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Documents
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className={`${isFullscreen ? 'min-h-screen bg-white py-6' : ''}`}>
      {isFullscreen && (
        <div className="flex items-center justify-between bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white rounded-2xl px-4 py-3 mx-6 md:mx-10 lg:mx-16 gap-4">
          <button
            onClick={() => navigate(`/portal/documents/${id}`)}
            className="px-3 py-1.5 bg-white/20 rounded-lg hover:bg-white/30 transition-colors"
          >
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
            >
              Full width
            </button>
          </div>
        </div>
      )}

      <div className={`space-y-6 ${contentWidth === 'reading' ? 'reading-mode' : ''} ${isFullscreen ? `w-full ${contentWidth === 'reading' ? 'max-w-5xl mx-auto' : 'max-w-none'} px-6 md:px-10 lg:px-16` : ''}`}>
        <div className="flex items-center justify-between">
          <Link
            to="/portal/documents"
            className="inline-flex items-center text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Documents
          </Link>
          {!isFullscreen && (
            <button
              onClick={() => navigate(`/portal/documents/${id}?fullscreen=1`)}
              className="btn-ghost"
            >
              Fullscreen
            </button>
          )}
        </div>

      {/* Document header */}
      <div className="surface-card rounded-2xl">
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-display font-bold text-slate-900">{document.title}</h1>
              {document.description && (
                <p className="mt-2 text-slate-600">{document.description}</p>
              )}
            </div>
            <span className="pill bg-emerald-100 text-emerald-700">
              v{document.version}
            </span>
          </div>

          {/* Metadata */}
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-500">
            {document.category && (
              <span className="inline-flex items-center">
                <Folder className="h-4 w-4 mr-1" />
                {document.category}
              </span>
            )}
            <span className="inline-flex items-center">
              <Clock className="h-4 w-4 mr-1" />
              Updated {formatDate(document.updated_at)}
            </span>
          </div>

          {/* Tags */}
          {document.tags.length > 0 && (
            <div className="mt-4 flex items-center gap-2">
              <Tag className="h-4 w-4 text-slate-400" />
              {document.tags.map((tag) => (
                <span
                  key={tag}
                  className="pill bg-sky-100 text-sky-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Document content */}
        <div className="p-6">
          <div
            ref={contentRef}
            className="prose max-w-none"
            dangerouslySetInnerHTML={{ __html: document.content }}
          />
        </div>
      </div>

      {/* Attachments */}
      {document.attachments.length > 0 && (
        <div className="surface-card rounded-2xl">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="text-lg font-display font-semibold text-slate-900 flex items-center">
              <Paperclip className="h-5 w-5 mr-2" />
              Attachments ({document.attachments.length})
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {document.attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-xl"
                >
                  <div className="flex items-center min-w-0">
                    <FileText className="h-8 w-8 text-slate-400 flex-shrink-0" />
                    <div className="ml-3 min-w-0">
                      <p className="font-medium text-slate-900 truncate">{attachment.filename}</p>
                      <p className="text-sm text-slate-500">
                        {formatFileSize(attachment.file_size)}
                        {attachment.mime_type && ` • ${attachment.mime_type}`}
                      </p>
                    </div>
                  </div>
                  <a
                    href={
                      attachment.download_url ?? `/api/v1/documents/${document.id}/attachments/${attachment.id}/download`
                    }
                    className="ml-4 flex items-center px-3 py-2 bg-sky-600 text-white text-sm rounded-xl hover:bg-sky-700"
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Download
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Feedback section */}
      <div className="surface-card rounded-2xl">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-display font-semibold text-slate-900">Submit Feedback</h2>
          <p className="text-sm text-slate-500">
            Have a question or suggestion about this document? Let us know!
          </p>
        </div>
        <div className="p-6">
          {feedbackSubmitted ? (
            <div className="text-center py-8">
              <CheckCircle className="h-12 w-12 mx-auto text-emerald-500" />
              <h3 className="mt-4 font-medium text-slate-900">Thank you for your feedback!</h3>
              <p className="mt-2 text-slate-500">
                We've received your submission and will respond soon.
              </p>
              <div className="mt-4 flex justify-center gap-4">
                <button
                  onClick={() => setFeedbackSubmitted(false)}
                  className="text-sky-600 hover:text-sky-500"
                >
                  Submit another
                </button>
                <Link to="/portal/feedback" className="text-sky-600 hover:text-sky-500">
                  View my feedback
                </Link>
              </div>
            </div>
          ) : (
            <FeedbackForm
              onSubmit={(data) => feedbackMutation.mutate(data)}
              isLoading={feedbackMutation.isPending}
              error={feedbackMutation.error?.message}
            />
          )}
        </div>
      </div>
      </div>
    </div>
  )
}
