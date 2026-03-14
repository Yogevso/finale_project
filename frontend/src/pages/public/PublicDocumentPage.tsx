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
  LogIn
} from 'lucide-react'
import { publicApi } from '@/lib/publicApi'
import { parseDocumentHtml } from '@/lib/documentRenderer'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import NotFoundState from '@/components/NotFoundState'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'
import { SEO } from '@/components/SEO'

export default function PublicDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const documentId = parseInt(id || '0')
  const location = useLocation()
  const navigate = useNavigate()
  const isFullscreen = location.search.includes('fullscreen=1')
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  // Fetch document
  const { data: doc, isLoading, error } = useQuery({
    queryKey: ['public-document', documentId],
    queryFn: () => publicApi.getDocument(documentId),
    enabled: documentId > 0,
  })
  const renderedContent = useMemo(() => parseDocumentHtml(doc?.content ?? ''), [doc?.content])

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const metaPills = [
    { label: doc?.category, icon: 'Category' },
    { label: doc?.platform, icon: 'Platform' },
  ].filter((item) => item.label)

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 rounded-xl w-1/2 mb-4" />
          <div className="h-4 bg-slate-200 rounded-xl w-1/4 mb-8" />
          <div className="space-y-3">
            <div className="h-4 bg-slate-200 rounded-xl" />
            <div className="h-4 bg-slate-200 rounded-xl" />
            <div className="h-4 bg-slate-200 rounded-xl w-3/4" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !doc) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16">
        <NotFoundState
          title="Document Not Found"
          description="This document doesn't exist or is not publicly accessible."
          icon={<FileText className="h-12 w-12 text-slate-300" />}
          action={
            <Link
              to="/docs"
              className="inline-flex items-center gap-2 text-sky-600 hover:text-sky-700 font-medium"
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
    <div className={`${isFullscreen ? 'min-h-screen bg-white' : 'min-h-screen bg-slate-50'}`}>
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
        <div className={`${isFullscreen ? (contentWidth === 'reading' ? 'max-w-5xl mx-auto' : 'max-w-none') : 'max-w-5xl mx-auto'} px-6 py-12`}>
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
            className="inline-flex items-center gap-2 text-sky-100/80 hover:text-white mb-5"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to documents
          </Link>
          <div className="flex items-start gap-4">
            <div className="bg-white/10 rounded-xl p-3">
              <FileText className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1">
              <div className="text-xs uppercase tracking-widest text-sky-200">Viewer Portal</div>
              <h1 className="text-3xl md:text-4xl font-display font-bold mt-2">{doc.title}</h1>
              <p className="text-sky-100 mt-2">{doc.document_number}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-4 mt-6 text-sm text-sky-100/80">
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
                className="btn-secondary"
              >
                Fullscreen
              </button>
            </div>
          )}
        </div>
      </section>

      <section className={`${contentWidth === 'reading' ? 'reading-mode' : ''} ${isFullscreen ? `w-full ${contentWidth === 'reading' ? 'max-w-4xl mx-auto' : 'max-w-none'} px-6 md:px-10 lg:px-16` : 'max-w-4xl mx-auto px-4'} py-10`}>
        {/* Category / Platform */}
        {metaPills.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {metaPills.map((item) => (
              <span
                key={`${item.icon}-${item.label}`}
                className="pill bg-slate-100 text-slate-600 border-slate-200"
              >
                {item.label}
              </span>
            ))}
          </div>
        )}

        {/* Tags */}
        {doc.tags && (
          <div className="flex flex-wrap gap-2 mb-6">
            {doc.tags.split(',').map((tag, i) => (
              <span
                key={i}
                className="pill bg-white text-slate-600 border-slate-200"
              >
                {tag.trim()}
              </span>
            ))}
          </div>
        )}

        {/* Description */}
        {doc.description && (
          <section className="mb-8">
            <h2 className="text-lg font-display font-semibold text-slate-900 mb-3">Description</h2>
            <p className="text-slate-600 leading-relaxed">{doc.description}</p>
          </section>
        )}

        {/* Document Content */}
        {doc.content && (
          <section className="mb-8">
            <h2 className="text-lg font-display font-semibold text-slate-900 mb-3">Content</h2>
            <div className="prose prose-slate max-w-none surface-card rounded-2xl p-6">
              <div className="whitespace-pre-wrap">{renderedContent}</div>
            </div>
          </section>
        )}

        {/* Attachments */}
        {doc.attachments && doc.attachments.length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-display font-semibold text-slate-900 mb-3 flex items-center gap-2">
              <Paperclip className="h-5 w-5" />
              Attachments ({doc.attachments.length})
            </h2>
            <div className="surface-card rounded-2xl divide-y divide-slate-100">
              {doc.attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-4 hover:bg-slate-50"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-slate-400" />
                    <div>
                      <p className="font-medium text-slate-900">{attachment.filename}</p>
                      <p className="text-sm text-slate-500">
                        {formatFileSize(attachment.file_size)} • {attachment.content_type}
                      </p>
                    </div>
                  </div>
                  <Link
                    to="/login"
                    className="flex items-center gap-2 text-sky-600 hover:text-sky-700 text-sm font-medium"
                  >
                    <Download className="h-4 w-4" />
                    Login to download
                  </Link>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Login CTA */}
        <section className="bg-sky-50 rounded-2xl p-6 text-center">
          <h3 className="text-lg font-display font-semibold text-slate-900 mb-2">
            Want access to more documents?
          </h3>
          <p className="text-slate-600 mb-4">
            Login to access internal documentation, download attachments, and more.
          </p>
          <Link
            to="/login"
            className="btn-primary inline-flex items-center gap-2"
          >
            <LogIn className="h-4 w-4" />
            Login
          </Link>
        </section>
      </section>
    </div>
  )
}
