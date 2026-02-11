import { useState } from 'react'
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import NotFoundState from '@/components/NotFoundState'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'

export default function ViewerDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const [isPrintMode, setIsPrintMode] = useState(false)
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))
  const location = useLocation()
  const navigate = useNavigate()
  const isFullscreen = location.search.includes('fullscreen=1')

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  // Fetch document details
  const { data: document, isLoading: docLoading, error } = useQuery({
    queryKey: ['viewer-document', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}`)
      if (!response.ok) {
        if (response.status === 404) throw new Error('Document not found')
        throw new Error('Failed to fetch document')
      }
      return response.json()
    },
    enabled: !!id,
  })

  // Fetch versions
  const { data: versions = [] } = useQuery({
    queryKey: ['viewer-document-versions', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}/versions`)
      if (!response.ok) return []
      return response.json()
    },
    enabled: !!id,
  })

  // Fetch attachments
  const { data: attachments = [] } = useQuery({
    queryKey: ['viewer-document-attachments', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}/attachments`)
      if (!response.ok) return []
      return response.json()
    },
    enabled: !!id,
  })

  // Fetch comments
  const { data: comments = [] } = useQuery({
    queryKey: ['viewer-document-comments', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}/comments`)
      if (!response.ok) return []
      return response.json()
    },
    enabled: !!id,
  })

  if (docLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8">
          <div className="surface-card rounded-2xl p-8 animate-pulse">
            <div className="h-8 bg-slate-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-slate-100 rounded w-1/4 mb-8"></div>
            <div className="space-y-3">
              <div className="h-4 bg-slate-100 rounded w-full"></div>
              <div className="h-4 bg-slate-100 rounded w-full"></div>
              <div className="h-4 bg-slate-100 rounded w-2/3"></div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-16">
          <NotFoundState
            title="Document Not Found"
            description="The document you're looking for doesn't exist or is not published."
            action={
              <Link to="/viewer" className="btn-primary inline-block">
                ← Back to Documents
              </Link>
            }
          />
        </main>
      </div>
    )
  }

  const isSyntheticUploadPlaceholder = (value?: string | null) => {
    if (!value) return false
    return value.trim().toLowerCase().startsWith('uploaded from file:')
  }

  const hasRenderableContent = (value?: string | null) => {
    if (!value) return false
    const trimmed = value.trim()
    return trimmed.length > 0 && !isSyntheticUploadPlaceholder(trimmed)
  }

  const normalizedVersions = Array.isArray(versions) ? versions : []
  const latestVersion =
    normalizedVersions.find((v: any) => v.is_published && hasRenderableContent(v.content)) ||
    normalizedVersions.find((v: any) => hasRenderableContent(v.content))
  const fallbackDocumentContent = hasRenderableContent((document as { content?: string | null }).content)
    ? (document as { content?: string | null }).content || ''
    : ''
  const content = typeof latestVersion?.content === 'string' ? latestVersion.content : fallbackDocumentContent
  const isHtmlContent = /<\/?[a-z][\s\S]*>/i.test(content)
  const versionLabel = (version: { semantic_version?: string | null; version_number?: number }) =>
    version?.semantic_version || `${version?.version_number || 1}.0.0`
  const documentPaperClass =
    contentWidth === 'fluid'
      ? 'document-preview-paper document-preview-paper-fluid'
      : 'document-preview-paper'

  // Print-friendly view
  if (isPrintMode) {
    return (
      <div className="min-h-screen bg-white print:bg-white">
        {/* Print Header - hidden when printing */}
        <div className="print:hidden bg-slate-100 p-4 flex items-center justify-between">
          <button
            onClick={() => setIsPrintMode(false)}
            className="btn-ghost"
          >
            ← Back to Document
          </button>
          <button
            onClick={() => window.print()}
            className="btn-primary"
          >
            🖨️ Print Document
          </button>
        </div>

        {/* Printable Content */}
        <div className="max-w-3xl mx-auto p-8 print:p-0 print:max-w-none">
          {/* Document Header */}
          <div className="border-b-2 border-slate-300 pb-4 mb-6">
            <div className="flex justify-between text-sm text-slate-500 mb-2">
              <span>{document.document_number}</span>
              <span>{document.category || 'General'}</span>
            </div>
            <h1 className="text-3xl font-display font-bold text-slate-900 mb-2">
              {document.title}
            </h1>
            {document.description && (
              <p className="text-slate-600">{document.description}</p>
            )}
            <div className="mt-4 text-sm text-slate-500 flex gap-6">
              <span>Published: {new Date(document.updated_at).toLocaleDateString()}</span>
              {latestVersion && <span>Version: {versionLabel(latestVersion)}</span>}
            </div>
          </div>

          {/* Content */}
          <div className="prose prose-lg max-w-none mb-8">
            {content ? (
              isHtmlContent ? (
                <div
                  className="document-preview-content"
                  dangerouslySetInnerHTML={{ __html: content }}
                />
              ) : (
                <div className="whitespace-pre-wrap text-slate-700">{content}</div>
              )
            ) : (
              <p className="text-slate-400 italic">No content available.</p>
            )}
          </div>

          {/* Attachments List */}
          {attachments.length > 0 && (
            <div className="border-t border-slate-200 pt-4 mt-8">
              <h2 className="text-lg font-display font-semibold mb-2">Attachments</h2>
              <ul className="list-disc list-inside text-sm text-slate-600">
                {attachments.map((a: any) => (
                  <li key={a.id}>{a.filename} ({formatFileSize(a.file_size)})</li>
                ))}
              </ul>
            </div>
          )}

          {/* Print Footer */}
          <div className="border-t border-slate-200 pt-4 mt-8 text-xs text-slate-400 print:block">
            <p>Printed from Documentation Platform • {new Date().toLocaleDateString()}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`${isFullscreen ? 'fixed inset-0 bg-white' : 'min-h-screen bg-gradient-to-br from-slate-50 to-sky-50'}`}>
      {!isFullscreen ? (
        <Header />
      ) : (
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg gap-4">
          <button
            onClick={() => navigate(`/viewer/documents/${id}`)}
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

      <main className={`${contentWidth === 'reading' ? 'reading-mode' : ''} ${isFullscreen ? `h-[calc(100vh-56px)] overflow-y-auto w-full ${contentWidth === 'reading' ? 'max-w-4xl mx-auto' : 'max-w-none'} px-6 md:px-10 lg:px-16` : `${contentWidth === 'reading' ? 'max-w-4xl mx-auto px-4' : 'max-w-none px-6 md:px-10 lg:px-16'}`} py-8`}>
        {/* Breadcrumb */}
        <nav className="mb-6 text-sm flex items-center justify-between">
          <Link to="/viewer" className="text-sky-600 hover:underline">
            Documents
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">/</span>
            <span className="text-slate-600">{document.title}</span>
          </div>
          {!isFullscreen && (
            <button
              onClick={() => navigate(`/viewer/documents/${id}?fullscreen=1`)}
              className="btn-ghost text-sm"
            >
              Fullscreen
            </button>
          )}
        </nav>

        {/* Document Header */}
        <div className="surface-card rounded-2xl p-8 mb-6">
          <div className="flex items-start justify-between mb-4">
            <span className="pill bg-sky-100 text-sky-700">
              {document.category || 'General'}
            </span>
            <span className="text-sm text-slate-400 font-mono">
              {document.document_number}
            </span>
          </div>

          <h1 className="text-3xl font-display font-bold text-slate-900 mb-4">
            {document.title}
          </h1>

          {document.description && (
            <p className="text-lg text-slate-600 mb-6">{document.description}</p>
          )}

          <div className="flex flex-wrap gap-6 text-sm text-slate-500 border-t border-slate-200 pt-4">
            <div>
              <span className="font-medium text-slate-700">Published:</span>{' '}
              {new Date(document.updated_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
            {latestVersion && (
              <div>
                <span className="font-medium text-slate-700">Version:</span>{' '}
                {versionLabel(latestVersion)}
              </div>
            )}
            <div className="ml-auto flex gap-2">
              <button
                onClick={() => setIsPrintMode(true)}
                className="btn-ghost text-sm"
              >
                🖨️ Print View
              </button>
            </div>
          </div>
        </div>

        {/* Document Content */}
        <div className="surface-card rounded-2xl p-8 mb-6">
          <h2 className="text-xl font-display font-semibold text-slate-900 mb-4 flex items-center gap-2">
            📄 Content
          </h2>
          <div className="max-w-none">
            {content ? (
              isHtmlContent ? (
                <div className={documentPaperClass}>
                  <div
                    className="document-preview-content"
                    dangerouslySetInnerHTML={{ __html: content }}
                  />
                </div>
              ) : (
                <div className="prose prose-lg max-w-none">
                  <div className="whitespace-pre-wrap text-slate-700">{content}</div>
                </div>
              )
            ) : (
              <p className="text-slate-400 italic">No content available.</p>
            )}
          </div>
        </div>

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="surface-card rounded-2xl p-8 mb-6">
            <h2 className="text-xl font-display font-semibold text-slate-900 mb-4 flex items-center gap-2">
              📎 Attachments
              <span className="text-sm font-normal text-slate-400">
                ({attachments.length})
              </span>
            </h2>
            <div className="space-y-3">
              {attachments.map((attachment: any) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">
                      {getFileIcon(attachment.mime_type)}
                    </span>
                    <div>
                      <p className="font-medium text-slate-900">
                        {attachment.filename}
                      </p>
                      <p className="text-sm text-slate-500">
                        {formatFileSize(attachment.file_size)}
                      </p>
                    </div>
                  </div>
                  <a
                    href={`/api/v1/attachments/${attachment.id}/download`}
                    className="btn-primary text-sm"
                  >
                    Download
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Version History */}
        {versions.length > 0 && (
          <div className="surface-card rounded-2xl p-8 mb-6">
            <h2 className="text-xl font-display font-semibold text-slate-900 mb-4 flex items-center gap-2">
              📋 Version History
              <span className="text-sm font-normal text-slate-400">
                ({versions.length})
              </span>
            </h2>
            <div className="space-y-3">
              {versions.map((version: any) => (
                <div
                  key={version.id}
                  className={`p-4 rounded-xl border ${
                    version.is_published
                      ? 'border-emerald-200 bg-emerald-50'
                      : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-medium text-slate-900">
                        v{versionLabel(version)}
                      </span>
                      {version.is_published && (
                        <span className="pill bg-emerald-100 text-emerald-700">
                          Published
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-slate-500">
                      {new Date(version.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {(version.changes_summary || version.change_notes) && (
                    <p className="text-sm text-slate-600 mt-2">
                      {version.changes_summary || version.change_notes}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Comments */}
        {comments.length > 0 && (
          <div className="surface-card rounded-2xl p-8 mb-6">
            <h2 className="text-xl font-display font-semibold text-slate-900 mb-4 flex items-center gap-2">
              💬 Comments
              <span className="text-sm font-normal text-slate-400">
                ({comments.length})
              </span>
            </h2>
            <div className="space-y-4">
              {comments.map((comment: any) => (
                <div
                  key={comment.id}
                  className="p-4 bg-slate-50 rounded-xl border-l-4 border-sky-200"
                >
                  <p className="text-slate-700 mb-2">{comment.content}</p>
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span>
                      By {comment.author_name || `User #${comment.author_id}`}
                    </span>
                    <span>
                      {new Date(comment.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Back Link */}
        <div className="text-center pt-4">
          <Link
            to="/viewer"
            className="btn-ghost inline-block"
          >
            ← Back to All Documents
          </Link>
        </div>
      </main>

      {/* Footer */}
      {!isFullscreen && (
        <footer className="bg-white border-t border-slate-200 mt-16">
          <div className="max-w-7xl mx-auto px-4 py-8 text-center text-slate-500 text-sm">
            <p>Documentation Platform • Built with React + FastAPI</p>
          </div>
        </footer>
      )}
    </div>
  )
}

function Header() {
  return (
    <header className="bg-white shadow-sm border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <Link to="/viewer" className="flex items-center gap-2">
            <h1 className="text-2xl font-display font-bold text-slate-900">📚 Documentation Platform</h1>
          </Link>
          <Link
            to="/login"
            className="text-sm text-sky-600 hover:text-sky-700 font-medium"
          >
            Staff Login →
          </Link>
        </div>
      </div>
    </header>
  )
}

function getFileIcon(mimeType: string): string {
  if (mimeType?.startsWith('image/')) return '🖼️'
  if (mimeType?.includes('pdf')) return '📕'
  if (mimeType?.includes('word') || mimeType?.includes('document')) return '📘'
  if (mimeType?.includes('excel') || mimeType?.includes('spreadsheet')) return '📗'
  if (mimeType?.includes('zip') || mimeType?.includes('archive')) return '📦'
  return '📄'
}

function formatFileSize(bytes: number): string {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
