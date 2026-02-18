import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import NotFoundState from '@/components/NotFoundState'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import type {
  Attachment,
  AttachmentOutlineResponse,
  AttachmentOutlineItem,
  Comment,
  Document,
  Version,
} from '@/types'

export default function ViewerDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const [isPrintMode, setIsPrintMode] = useState(false)
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null)
  const [showTextMode, setShowTextMode] = useState(false)
  const [pdfOutlineItems, setPdfOutlineItems] = useState<AttachmentOutlineItem[]>([])
  const [pdfOutlineLoading, setPdfOutlineLoading] = useState(false)
  const [pdfOutlineError, setPdfOutlineError] = useState<string | null>(null)
  const [pdfOutlinePage, setPdfOutlinePage] = useState<number | null>(null)
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))
  const location = useLocation()
  const navigate = useNavigate()
  const isFullscreen = location.search.includes('fullscreen=1')

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  // Fetch document details
  const { data: document, isLoading: docLoading, error } = useQuery<Document>({
    queryKey: ['viewer-document', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}`)
      if (!response.ok) {
        if (response.status === 404) throw new Error('Document not found')
        throw new Error('Failed to fetch document')
      }
      return response.json() as Promise<Document>
    },
    enabled: !!id,
  })

  // Fetch versions
  const { data: versions = [] } = useQuery<Version[]>({
    queryKey: ['viewer-document-versions', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}/versions`)
      if (!response.ok) return []
      return response.json() as Promise<Version[]>
    },
    enabled: !!id,
  })

  const { data: selectedVersionAttachments = [], isLoading: selectedVersionAttachmentsLoading } =
    useQuery<Attachment[]>({
      queryKey: ['viewer-document-version-attachments', id, selectedVersionId],
      queryFn: async () => {
        if (!selectedVersionId) return []
        const response = await fetch(`/api/v1/viewer/documents/${id}/versions/${selectedVersionId}/attachments`)
        if (!response.ok) return []
        return response.json() as Promise<Attachment[]>
      },
      enabled: !!id && !!selectedVersionId,
    })

  // Fetch comments
  const { data: comments = [] } = useQuery<Comment[]>({
    queryKey: ['viewer-document-comments', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/viewer/documents/${id}/comments`)
      if (!response.ok) return []
      return response.json() as Promise<Comment[]>
    },
    enabled: !!id,
  })

  const isSyntheticUploadPlaceholder = (value?: string | null) => {
    if (!value) return false
    return value.trim().toLowerCase().startsWith('uploaded from file:')
  }

  const hasRenderableContent = (value?: string | null) => {
    if (!value) return false
    const trimmed = value.trim()
    return trimmed.length > 0 && !isSyntheticUploadPlaceholder(trimmed)
  }

  const normalizedVersions: Version[] = Array.isArray(versions) ? versions : []
  const requestedVersionId = Number(new URLSearchParams(location.search).get('version') || '')

  useEffect(() => {
    if (normalizedVersions.length === 0) {
      setSelectedVersionId(null)
      return
    }
    if (
      selectedVersionId &&
      normalizedVersions.some((version) => version.id === selectedVersionId)
    ) {
      return
    }
    if (
      Number.isInteger(requestedVersionId) &&
      requestedVersionId > 0 &&
      normalizedVersions.some((version) => version.id === requestedVersionId)
    ) {
      setSelectedVersionId(requestedVersionId)
      return
    }
    setSelectedVersionId(null)
  }, [normalizedVersions, requestedVersionId, selectedVersionId])

  useEffect(() => {
    setShowTextMode(false)
  }, [selectedVersionId])

  const handleVersionSelect = (versionId: number) => {
    setSelectedVersionId(versionId)
    const params = new URLSearchParams(location.search)
    params.set('version', String(versionId))
    navigate(
      {
        pathname: location.pathname,
        search: `?${params.toString()}`,
      },
      { replace: true },
    )
  }

  const selectedVersion =
    selectedVersionId === null
      ? null
      : normalizedVersions.find((version) => version.id === selectedVersionId) || null
  const effectiveAttachments = selectedVersionId ? selectedVersionAttachments : []
  const selectedPdfAttachment = effectiveAttachments.find((attachment) =>
    (attachment.mime_type || '').startsWith('application/pdf'),
  )
  const pdfPreviewUrl =
    selectedPdfAttachment && id
      ? `/api/v1/viewer/documents/${id}/attachments/${selectedPdfAttachment.id}/preview`
      : null
  const pdfPreviewSrc =
    pdfPreviewUrl && pdfOutlinePage ? `${pdfPreviewUrl}#page=${pdfOutlinePage}` : pdfPreviewUrl

  const contentSource =
    selectedVersion && hasRenderableContent(selectedVersion.content) ? selectedVersion.content : ''
  const content = typeof contentSource === 'string' ? contentSource : ''
  const isHtmlContent = /<\/?[a-z][\s\S]*>/i.test(content)
  const versionLabel = (version: { semantic_version?: string | null; version_number?: number }) =>
    version?.semantic_version || `${version?.version_number || 1}.0.0`
  const documentPaperClass =
    contentWidth === 'fluid'
      ? 'document-preview-paper document-preview-paper-fluid'
      : 'document-preview-paper'

  useEffect(() => {
    if (!selectedPdfAttachment || !id) {
      setPdfOutlineItems([])
      setPdfOutlineLoading(false)
      setPdfOutlineError(null)
      setPdfOutlinePage(null)
      return
    }

    let cancelled = false
    setPdfOutlineLoading(true)
    setPdfOutlineError(null)
    setPdfOutlinePage(null)

    fetch(`/api/v1/viewer/documents/${id}/attachments/${selectedPdfAttachment.id}/outline`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to load TOC')
        }
        return (await response.json()) as AttachmentOutlineResponse
      })
      .then((payload) => {
        if (cancelled) return
        setPdfOutlineItems(payload.items || [])
        setPdfOutlineError(payload.error || null)
      })
      .catch((outlineError) => {
        if (cancelled) return
        console.error('Failed loading PDF outline:', outlineError)
        setPdfOutlineItems([])
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
  }, [id, selectedPdfAttachment])

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
              {selectedVersion && <span>Version: {versionLabel(selectedVersion)}</span>}
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
          {effectiveAttachments.length > 0 && (
            <div className="border-t border-slate-200 pt-4 mt-8">
              <h2 className="text-lg font-display font-semibold mb-2">Attachments</h2>
              <ul className="list-disc list-inside text-sm text-slate-600">
                {effectiveAttachments.map((a) => (
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
            onClick={() => {
              const params = new URLSearchParams(location.search)
              params.delete('fullscreen')
              navigate(`/viewer/documents/${id}${params.toString() ? `?${params.toString()}` : ''}`)
            }}
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
              onClick={() => {
                const params = new URLSearchParams(location.search)
                params.set('fullscreen', '1')
                navigate(`/viewer/documents/${id}?${params.toString()}`)
              }}
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
            {selectedVersion && (
              <div>
                <span className="font-medium text-slate-700">Version:</span>{' '}
                {versionLabel(selectedVersion)}
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
            {!selectedVersion ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center">
                <p className="text-slate-700 font-medium">Select a version to load preview.</p>
                <p className="text-sm text-slate-500 mt-1">
                  Viewer does not auto-select the latest version.
                </p>
              </div>
            ) : selectedVersionAttachmentsLoading ? (
              <div className="h-[65vh] flex items-center justify-center">
                <div className="text-center text-slate-500">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-600 mx-auto mb-3"></div>
                  Loading version preview...
                </div>
              </div>
            ) : selectedPdfAttachment && pdfPreviewUrl ? (
              <div className="flex h-[70vh] rounded-xl border border-slate-200 overflow-hidden">
                <aside className="w-72 bg-slate-50 border-r border-slate-200 flex flex-col">
                  <div className="px-4 py-3 border-b border-slate-200 bg-white">
                    <h3 className="text-sm font-semibold text-slate-800">Contents</h3>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    {pdfOutlineLoading ? (
                      <div className="p-4 text-sm text-slate-500">Loading TOC...</div>
                    ) : pdfOutlineItems.length > 0 ? (
                      <nav className="p-2 space-y-1">
                        {pdfOutlineItems.map((item) => {
                          const pageStart = item.page_start || item.page
                          return (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => setPdfOutlinePage(pageStart)}
                              className={`w-full text-left px-2 py-1.5 text-sm rounded hover:bg-sky-100 hover:text-sky-800 ${
                                pdfOutlinePage === pageStart
                                  ? 'bg-sky-100 text-sky-800 font-medium'
                                  : 'text-slate-700'
                              }`}
                              style={{ paddingLeft: `${Math.max(0, item.level - 1) * 14 + 8}px` }}
                            >
                              <span className="truncate block">{item.title}</span>
                            </button>
                          )
                        })}
                      </nav>
                    ) : (
                      <div className="p-4 text-sm text-slate-500">
                        {pdfOutlineError || 'No TOC available'}
                      </div>
                    )}
                  </div>
                </aside>
                <iframe
                  key={`${selectedVersion.id}-${selectedPdfAttachment.id}`}
                  src={pdfPreviewSrc || undefined}
                  className="flex-1 h-full"
                  title={`${document.title} PDF Preview`}
                />
              </div>
            ) : showTextMode && content ? (
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
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
                <p className="text-amber-900 font-medium">
                  No PDF attachment is available for the selected version.
                </p>
                <p className="text-sm text-amber-800 mt-1">
                  Visual preview requires a PDF attachment for this version.
                </p>
                {content && (
                  <button
                    type="button"
                    onClick={() => setShowTextMode(true)}
                    className="mt-4 btn-secondary text-sm"
                  >
                    Open Text Mode
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Attachments */}
        {effectiveAttachments.length > 0 && (
          <div className="surface-card rounded-2xl p-8 mb-6">
            <h2 className="text-xl font-display font-semibold text-slate-900 mb-4 flex items-center gap-2">
              📎 Attachments
              <span className="text-sm font-normal text-slate-400">
                ({effectiveAttachments.length})
              </span>
            </h2>
            <div className="space-y-3">
              {effectiveAttachments.map((attachment) => (
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
                    href={
                      id
                        ? `/api/v1/viewer/documents/${id}/attachments/${attachment.id}/download`
                        : '#'
                    }
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
              {versions.map((version) => (
                <button
                  key={version.id}
                  type="button"
                  onClick={() => handleVersionSelect(version.id)}
                  className={`p-4 rounded-xl border ${
                    selectedVersionId === version.id
                      ? 'border-sky-400 bg-sky-50'
                      : version.is_published
                      ? 'border-emerald-200 bg-emerald-50'
                      : 'border-slate-200 bg-slate-50'
                  } w-full text-left transition-colors hover:border-sky-300`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-medium text-slate-900">
                        v{versionLabel(version)}
                      </span>
                      {selectedVersionId === version.id && (
                        <span className="pill bg-sky-100 text-sky-700">Viewing</span>
                      )}
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
                  {version.changes_summary && (
                    <p className="text-sm text-slate-600 mt-2">
                      {version.changes_summary}
                    </p>
                  )}
                </button>
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
              {comments.map((comment) => (
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
