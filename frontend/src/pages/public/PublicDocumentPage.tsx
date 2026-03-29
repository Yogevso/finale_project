import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  ArrowLeft,
  Download,
  Calendar,
  Tag,
  Folder,
  Paperclip,
  Clock,
  LogIn,
} from 'lucide-react'
import { publicApi } from '@/lib/publicApi'
import { audienceSensitiveQueryOptions } from '@/lib/queryFreshness'
import { parseDocumentHtml } from '@/lib/documentRenderer'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import { useTheme } from '@/hooks/useTheme'
import NotFoundState from '@/components/NotFoundState'
import Skeleton from '@/components/Skeleton'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'
import { SEO } from '@/components/SEO'

export default function PublicDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const documentId = parseInt(id || '0')
  const location = useLocation()
  const navigate = useNavigate()
  const isFullscreen = location.search.includes('fullscreen=1')
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))
  const { theme } = useTheme()

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  const { data: doc, isLoading, error } = useQuery({
    queryKey: ['public-document', documentId],
    queryFn: () => publicApi.getDocument(documentId),
    enabled: documentId > 0,
    ...audienceSensitiveQueryOptions,
  })
  const renderedContent = useMemo(() => parseDocumentHtml(doc?.content ?? ''), [doc?.content])

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const metaPills = [
    { label: doc?.category, icon: 'Category' },
    { label: doc?.platform, icon: 'Platform' },
  ].filter((item) => item.label)

  const documentPaperClass =
    `${contentWidth === 'fluid' ? 'document-preview-paper document-preview-paper-fluid' : 'document-preview-paper'} ${
      theme === 'dark' ? 'document-preview-paper--dark' : 'document-preview-paper--light'
    }`

  if (isLoading) {
    return (
      <div className="content-shell max-w-4xl animate-fade-in py-8">
        <Skeleton className="mb-4 h-8 w-1/2" />
        <Skeleton className="mb-8 h-4 w-1/4" />
        <div className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    )
  }

  if (error || !doc) {
    const is404 = error instanceof Error && error.message.includes('not found')
    return (
      <div className="content-shell max-w-4xl animate-fade-in py-16">
        <NotFoundState
          title={is404 ? 'Document Not Found' : 'Failed to Load Document'}
          description={
            is404
              ? "This document doesn't exist or is not publicly accessible."
              : 'A network error occurred. Please check your connection and try again.'
          }
          icon={<FileText className="h-12 w-12 text-slate-300 dark:text-slate-600" />}
          action={
            <Link
              to="/docs"
              className="btn-secondary table-action-btn inline-flex"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to documents
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className={`${isFullscreen ? 'min-h-screen bg-white dark:bg-slate-950' : 'min-h-screen bg-slate-50 dark:bg-slate-950'} animate-fade-in`}>
      <SEO
        title={doc.title}
        description={doc.description || `Read ${doc.title} on our documentation platform.`}
        image={doc.thumbnail_url}
        type="article"
      />
      <FullscreenTopBar
        isFullscreen={isFullscreen}
        documentTitle={doc.title}
        contentWidth={contentWidth}
        onExitFullscreen={() => navigate(`/doc/${documentId}`)}
        onSetReadingWidth={() => applyWidth('reading')}
        onSetFluidWidth={() => applyWidth('fluid')}
        wrapperClassName="px-4"
      />

      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div
          className={`${isFullscreen ? (contentWidth === 'reading' ? 'mx-auto max-w-5xl' : 'max-w-none') : 'content-shell max-w-5xl'} px-6 py-12`}
        >
          <nav className="mb-5 flex flex-wrap items-center gap-2 text-sm text-sky-100/80">
            <Link to="/docs" className="hover:text-white">
              Home
            </Link>
            <span>/</span>
            <Link to="/docs" className="hover:text-white">
              {doc.category || 'Documents'}
            </Link>
            <span>/</span>
            <span className="truncate text-white">{doc.title}</span>
          </nav>
          <Link
            to="/docs"
            className="mb-5 inline-flex items-center gap-2 text-sky-100/80 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to documents
          </Link>
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-white/10 p-3">
              <FileText className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1">
              <div className="text-xs uppercase tracking-widest text-sky-200">Viewer Portal</div>
              <h1 className="mt-2 text-3xl font-display font-bold md:text-4xl">{doc.title}</h1>
              <p className="mt-2 text-sky-100">{doc.document_number}</p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-4 text-sm text-sky-100/80">
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              <span>Created {formatDate(doc.created_at)}</span>
            </div>
            {doc.updated_at && (
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <span>Updated {formatDate(doc.updated_at)}</span>
              </div>
            )}
            {doc.category && (
              <div className="flex items-center gap-1">
                <Folder className="h-4 w-4" />
                <span>{doc.category}</span>
              </div>
            )}
            {doc.version_number && (
              <div className="flex items-center gap-1">
                <Tag className="h-4 w-4" />
                <span>Version {doc.version_number}</span>
              </div>
            )}
          </div>
          {!isFullscreen && (
            <div className="mt-4">
              <button
                onClick={() => navigate(`/doc/${documentId}?fullscreen=1`)}
                className="btn-secondary table-action-btn"
                type="button"
              >
                Fullscreen
              </button>
            </div>
          )}
        </div>
      </section>

      <section
        className={`${contentWidth === 'reading' ? 'reading-mode' : ''} ${
          isFullscreen
            ? `w-full ${contentWidth === 'reading' ? 'mx-auto max-w-4xl' : 'max-w-none'} px-6 md:px-10 lg:px-16`
            : 'content-shell max-w-4xl'
        } py-10`}
      >
        {metaPills.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {metaPills.map((item) => (
              <span
                key={`${item.icon}-${item.label}`}
                className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                {item.label}
              </span>
            ))}
          </div>
        )}

        {doc.tags && (
          <div className="mb-6 flex flex-wrap gap-2">
            {doc.tags.split(',').map((tag, i) => (
              <span
                key={i}
                className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                {tag.trim()}
              </span>
            ))}
          </div>
        )}

        {doc.description && (
          <section className="mb-8">
            <h2 className="section-title mb-3">
              Description
            </h2>
            <p className="body-copy leading-relaxed">{doc.description}</p>
          </section>
        )}

        {doc.content && (
          <section className="mb-8">
            <h2 className="section-title mb-3">
              Content
            </h2>
            <div className={`${documentPaperClass} rounded-2xl`}>
              <div className="document-preview-content">{renderedContent}</div>
            </div>
          </section>
        )}

        {doc.attachments && doc.attachments.length > 0 && (
          <section className="mb-8">
            <h2 className="section-title mb-3 flex items-center gap-2">
              <Paperclip className="h-5 w-5" />
              Attachments ({doc.attachments.length})
            </h2>
            <div className="surface-card divide-y divide-slate-100 rounded-2xl dark:divide-slate-800">
              {doc.attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-4 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                    <div>
                      <p className="card-title">{attachment.filename}</p>
                      <p className="helper-copy">
                        {formatFileSize(attachment.file_size)} | {attachment.content_type}
                      </p>
                    </div>
                  </div>
                  <Link
                    to="/login"
                    className="btn-secondary table-action-btn"
                  >
                    <Download className="h-4 w-4" />
                    Login to download
                  </Link>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="rounded-2xl bg-sky-50 p-6 text-center dark:bg-sky-950/40">
          <h3 className="section-title mb-2">
            Want access to more documents?
          </h3>
          <p className="body-copy mb-4">
            Login to access internal documentation, download attachments, and more.
          </p>
          <Link to="/login" className="btn-primary inline-flex items-center gap-2">
            <LogIn className="h-4 w-4" />
            Login
          </Link>
        </section>
      </section>
    </div>
  )
}
