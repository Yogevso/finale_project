/**
 * CustomerDocumentPage - Document detail view for customer portal
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portalApi, type FeedbackItem, type FeedbackListResponse } from '../../lib/portalApi'
import { useAuth } from '@/lib/auth'
import { parseDocumentHtml } from '@/lib/documentRenderer'
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
  BookOpen,
  LifeBuoy,
} from 'lucide-react'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import NotFoundState from '@/components/NotFoundState'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'

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

  const { data: document, isLoading, error } = useQuery({
    queryKey: ['portal', 'document', id],
    queryFn: () => portalApi.getDocument(Number(id)),
    enabled: !!id,
  })
  const renderedContent = useMemo(() => parseDocumentHtml(document?.content ?? ''), [document?.content])

  const { data: relatedDocs } = useQuery({
    queryKey: ['portal', 'document', id, 'related'],
    queryFn: () => portalApi.getRelatedDocuments(Number(id)),
    enabled: !!id,
  })

  const feedbackMutation = useMutation({
    mutationFn: (data: { feedback_type: 'question' | 'suggestion' | 'issue' | 'other'; content: string }) =>
      portalApi.submitFeedback({
        document_id: Number(id),
        ...data,
      }),
    onMutate: async (data) => {
      setFeedbackSubmitted(true)

      const optimisticFeedbackId = -Date.now()
      const nowIso = new Date().toISOString()
      const optimisticFeedback: FeedbackItem = {
        id: optimisticFeedbackId,
        document_id: Number(id),
        document_title: document?.title || 'Current document',
        feedback_type: data.feedback_type,
        content: data.content,
        status: 'pending',
        created_at: nowIso,
        updated_at: nowIso,
      }

      const previousFeedbackQueries = queryClient.getQueriesData<FeedbackListResponse>({
        queryKey: ['portal', 'feedback'],
      })

      previousFeedbackQueries.forEach(([queryKey, previous]) => {
        if (!previous) return

        const filters =
          Array.isArray(queryKey) && typeof queryKey[2] === 'object' && queryKey[2] !== null
            ? (queryKey[2] as { status?: 'pending' | 'responded' | 'closed' })
            : undefined

        if (filters?.status && filters.status !== 'pending') {
          return
        }

        queryClient.setQueryData<FeedbackListResponse>(queryKey, {
          ...previous,
          items: [optimisticFeedback, ...previous.items],
          total: previous.total + 1,
        })
      })

      return { optimisticFeedbackId, previousFeedbackQueries }
    },
    onError: (_error, _variables, context) => {
      setFeedbackSubmitted(false)
      context?.previousFeedbackQueries.forEach(([queryKey, previous]) => {
        queryClient.setQueryData(queryKey, previous)
      })
    },
    onSuccess: (createdFeedback, _variables, context) => {
      queryClient.setQueriesData<FeedbackListResponse>(
        { queryKey: ['portal', 'feedback'] },
        (current) => {
          if (!current) return current
          return {
            ...current,
            items: current.items.map((item) =>
              item.id === context?.optimisticFeedbackId ? createdFeedback : item,
            ),
          }
        },
      )
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['portal', 'feedback'] })
    },
  })

  const updateProgressMutation = useMutation({
    mutationFn: (percent: number) => portalApi.updateReadingProgress(Number(id), percent),
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
      <div className="content-shell flex animate-fade-in justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-sky-600"></div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="content-shell animate-fade-in py-12">
        <NotFoundState
          title="Document Not Found"
          description="This document may not exist or you don't have access to view it."
          icon={<FileText className="h-12 w-12 text-slate-300 dark:text-slate-600" />}
          action={
            <Link
              to="/portal/documents"
              className="btn-secondary table-action-btn inline-flex items-center gap-2"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Documents
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className={`${isFullscreen ? 'min-h-screen bg-white py-6 dark:bg-slate-950' : 'page-stack'} animate-fade-in`}>
      <FullscreenTopBar
        isFullscreen={isFullscreen}
        documentTitle={document.title}
        contentWidth={contentWidth}
        onExitFullscreen={() => navigate(`/portal/documents/${id}`)}
        onSetReadingWidth={() => applyWidth('reading')}
        onSetFluidWidth={() => applyWidth('fluid')}
        wrapperClassName="mx-6 rounded-2xl px-4 md:mx-10 lg:mx-16"
      />

      <div
        className={`space-y-6 ${contentWidth === 'reading' ? 'reading-mode' : ''} ${isFullscreen ? `w-full ${contentWidth === 'reading' ? 'mx-auto max-w-5xl' : 'max-w-none'} px-6 md:px-10 lg:px-16` : ''}`}
      >
        <div className="flex items-center justify-between">
          <Link
            to="/portal/documents"
            className="btn-ghost table-action-btn inline-flex items-center gap-2"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Documents
          </Link>
          {!isFullscreen && (
            <button
              type="button"
              onClick={() => navigate(`/portal/documents/${id}?fullscreen=1`)}
              className="btn-ghost table-action-btn"
            >
              Fullscreen
            </button>
          )}
        </div>

        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 p-6 dark:border-slate-800">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="page-title text-slate-900 dark:text-slate-100">
                  {document.title}
                </h1>
                {document.description && (
                  <p className="body-copy mt-2 dark:text-slate-300">{document.description}</p>
                )}
              </div>
              <span className="pill border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200">
                v{document.version}
              </span>
            </div>

            <div className="helper-copy mt-4 flex flex-wrap gap-4 dark:text-slate-400">
              {document.category && (
                <span className="inline-flex items-center">
                  <Folder className="mr-1 h-4 w-4" />
                  {document.category}
                </span>
              )}
              <span className="inline-flex items-center">
                <Clock className="mr-1 h-4 w-4" />
                Updated {formatDate(document.updated_at)}
              </span>
            </div>

            {document.tags.length > 0 && (
              <div className="mt-4 flex items-center gap-2">
                <Tag className="h-4 w-4 text-slate-400 dark:text-slate-500" />
                {document.tags.map((tag) => (
                  <span
                    key={tag}
                    className="pill border-sky-200 bg-sky-100 text-sky-700 dark:border-sky-900 dark:bg-sky-950/50 dark:text-sky-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="p-6">
            <div ref={contentRef} className="prose prose-slate max-w-none dark:prose-invert">
              {renderedContent}
            </div>
          </div>
        </div>

        {document.attachments.length > 0 && (
          <div className="surface-card rounded-2xl">
            <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <h2 className="section-title flex items-center dark:text-slate-100">
                <Paperclip className="mr-2 h-5 w-5" />
                Attachments ({document.attachments.length})
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {document.attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-950"
                  >
                    <div className="flex min-w-0 items-center">
                      <FileText className="h-8 w-8 flex-shrink-0 text-slate-400 dark:text-slate-500" />
                      <div className="ml-3 min-w-0">
                        <p className="card-title truncate dark:text-slate-100">
                          {attachment.filename}
                        </p>
                        <p className="helper-copy dark:text-slate-400">
                          {formatFileSize(attachment.file_size)}
                          {attachment.mime_type && ` - ${attachment.mime_type}`}
                        </p>
                      </div>
                    </div>
                    <a
                      href={
                        attachment.download_url ??
                        `/api/v1/documents/${document.id}/attachments/${attachment.id}/download`
                      }
                      className="btn-primary table-action-btn ml-4"
                    >
                      <Download className="mr-1 h-4 w-4" />
                      Download
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {relatedDocs && relatedDocs.length > 0 && (
          <div className="surface-card rounded-2xl">
            <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <h2 className="section-title flex items-center dark:text-slate-100">
                <BookOpen className="mr-2 h-5 w-5" />
                Related Documents
              </h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {relatedDocs.map((related) => (
                  <Link
                    key={related.id}
                    to={`/portal/documents/${related.id}`}
                    className="surface-card-hover block rounded-2xl p-4"
                  >
                    <h3 className="card-title line-clamp-2 dark:text-slate-100">
                      {related.title}
                    </h3>
                    {related.description && (
                      <p className="body-copy mt-1 line-clamp-2 dark:text-slate-400">
                        {related.description}
                      </p>
                    )}
                    <div className="helper-copy mt-2 flex items-center gap-2 dark:text-slate-500">
                      {related.category && (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800 dark:text-slate-200">
                          {related.category}
                        </span>
                      )}
                      {related.updated_at && <span>{formatDate(related.updated_at)}</span>}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <h2 className="section-title dark:text-slate-100">
              Submit Feedback
            </h2>
            <p className="body-copy dark:text-slate-400">
              Have a question or suggestion about this document? Let us know!
            </p>
          </div>
          <div className="p-6">
            {feedbackSubmitted ? (
              <div className="py-8 text-center">
                <CheckCircle className="mx-auto h-12 w-12 text-emerald-500" />
                <h3 className="section-title mt-4 text-base dark:text-slate-100">
                  Thank you for your feedback!
                </h3>
                <p className="body-copy mt-2 dark:text-slate-400">
                  We've received your submission and will respond soon.
                </p>
                <div className="mt-4 flex justify-center gap-4">
                  <button
                    onClick={() => setFeedbackSubmitted(false)}
                    className="btn-secondary table-action-btn"
                    type="button"
                  >
                    Submit another
                  </button>
                  <Link to="/portal/feedback" className="btn-secondary table-action-btn">
                    View my feedback
                  </Link>
                  <Link to="/portal/support" className="btn-secondary table-action-btn">
                    View support tickets
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

        <div className="surface-card flex items-center justify-between rounded-2xl px-6 py-5">
          <div>
            <h2 className="section-title dark:text-slate-100">
              Need more help?
            </h2>
            <p className="body-copy dark:text-slate-400">
              Open a support ticket with this document's context pre-filled.
            </p>
          </div>
          <Link
            to={`/portal/support?new=1&subject=${encodeURIComponent(`Help with: ${document?.title ?? 'Document #' + id}`)}&content=${encodeURIComponent(`Document: ${document?.title ?? ''} (ID: ${id})\nURL: ${window.location.href}\nBrowser: ${navigator.userAgent}\n\nDescribe your issue:\n`)}`}
            className="btn-primary table-action-btn inline-flex items-center gap-2 whitespace-nowrap"
          >
            <LifeBuoy className="h-4 w-4" />
            Contact Support
          </Link>
        </div>
      </div>
    </div>
  )
}
