import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import NotFoundState from '@/components/NotFoundState'
import { parseDocumentHtml } from '@/lib/documentRenderer'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import { audienceSensitiveQueryOptions, fetchFresh } from '@/lib/queryFreshness'
import { useTheme } from '@/hooks/useTheme'
import { formatDocumentDate } from '@/lib/dateUtils'
import type {
  Attachment,
  Document,
  Version,
} from '@/types'

export default function ViewerDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const [isPrintMode, setIsPrintMode] = useState(false)
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null)
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))
  const location = useLocation()
  const navigate = useNavigate()
  const { theme } = useTheme()
  const isFullscreen = location.search.includes('fullscreen=1')

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }

  const { data: document, isLoading: docLoading, error } = useQuery<Document>({
    queryKey: ['viewer-document', id],
    queryFn: async () => {
      const response = await fetchFresh(`/api/v1/viewer/documents/${id}`)
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Document not found')
        }
        throw new Error('Failed to fetch document')
      }
      return response.json() as Promise<Document>
    },
    enabled: !!id,
    ...audienceSensitiveQueryOptions,
  })

  const { data: versions = [] } = useQuery<Version[]>({
    queryKey: ['viewer-document-versions', id],
    queryFn: async () => {
      const response = await fetchFresh(`/api/v1/viewer/documents/${id}/versions`)
      if (!response.ok) {
        return []
      }
      return response.json() as Promise<Version[]>
    },
    enabled: !!id,
    ...audienceSensitiveQueryOptions,
  })

  const { data: selectedVersionAttachments = [], isLoading: selectedVersionAttachmentsLoading } =
    useQuery<Attachment[]>({
      queryKey: ['viewer-document-version-attachments', id, selectedVersionId],
      queryFn: async () => {
        if (!selectedVersionId) {
          return []
        }
        const response = await fetchFresh(`/api/v1/viewer/documents/${id}/versions/${selectedVersionId}/attachments`)
        if (!response.ok) {
          return []
        }
        return response.json() as Promise<Attachment[]>
      },
      enabled: !!id && !!selectedVersionId,
      ...audienceSensitiveQueryOptions,
    })

  const isSyntheticUploadPlaceholder = (value?: string | null) => {
    if (!value) {
      return false
    }
    return value.trim().toLowerCase().startsWith('uploaded from file:')
  }

  const hasRenderableContent = (value?: string | null) => {
    if (!value) {
      return false
    }
    const trimmed = value.trim()
    return trimmed.length > 0 && !isSyntheticUploadPlaceholder(trimmed)
  }

  const normalizedVersions = useMemo<Version[]>(
    () => (Array.isArray(versions) ? versions : []),
    [versions],
  )
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
    // Auto-select latest published version, or first version as fallback
    const latestPublished = normalizedVersions
      .filter((v) => v.is_published)
      .sort((a, b) => b.version_number - a.version_number)[0]
    setSelectedVersionId(latestPublished?.id ?? normalizedVersions[0]?.id ?? null)
  }, [normalizedVersions, requestedVersionId, selectedVersionId])

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

  const contentSource =
    selectedVersion && hasRenderableContent(selectedVersion.content) ? selectedVersion.content : ''
  const content = typeof contentSource === 'string' ? contentSource : ''
  const isHtmlContent = /<\/?[a-z][\s\S]*>/i.test(content)
  const renderedContent = useMemo(() => parseDocumentHtml(content), [content])
  const versionLabel = (version: { semantic_version?: string | null; version_number?: number }) =>
    version?.semantic_version || `${version?.version_number || 1}.0.0`
  const documentPaperClass =
    `${contentWidth === 'fluid' ? 'document-preview-paper document-preview-paper-fluid' : 'document-preview-paper'} ${
      theme === 'dark' ? 'document-preview-paper--dark' : 'document-preview-paper--light'
    }`

  if (docLoading) {
    return (
      <div className="min-h-screen animate-fade-in bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900">
        <Header />
        <main className="content-shell max-w-4xl py-8">
          <div className="surface-card animate-pulse rounded-2xl p-8">
            <div className="mb-4 h-8 w-3/4 rounded bg-slate-200 dark:bg-slate-800"></div>
            <div className="mb-8 h-4 w-1/4 rounded bg-slate-100 dark:bg-slate-900"></div>
            <div className="space-y-3">
              <div className="h-4 w-full rounded bg-slate-100 dark:bg-slate-900"></div>
              <div className="h-4 w-full rounded bg-slate-100 dark:bg-slate-900"></div>
              <div className="h-4 w-2/3 rounded bg-slate-100 dark:bg-slate-900"></div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="min-h-screen animate-fade-in bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900">
        <Header />
        <main className="content-shell max-w-4xl py-16">
          <NotFoundState
            title="Document Not Found"
            description="The document you're looking for doesn't exist or is not published."
            action={
              <Link to="/viewer" className="btn-primary table-action-btn inline-flex">
                Back to Documents
              </Link>
            }
          />
        </main>
      </div>
    )
  }

  if (isPrintMode) {
    return (
      <div className="min-h-screen animate-fade-in bg-white print:bg-white">
        <div className="flex items-center justify-between bg-slate-100 p-4 print:hidden">
          <button onClick={() => setIsPrintMode(false)} className="btn-ghost" type="button">
            Back to Document
          </button>
          <button onClick={() => window.print()} className="btn-primary" type="button">
            Print Document
          </button>
        </div>

        <div className="mx-auto max-w-3xl p-8 print:max-w-none print:p-0">
          <div className="mb-6 border-b-2 border-slate-300 pb-4">
            <div className="mb-2 flex justify-between text-sm text-slate-500">
              <span>{document.document_number}</span>
              <span>{document.category || 'General'}</span>
            </div>
            <h1 className="mb-2 text-3xl font-display font-bold text-slate-900">
              {document.title}
            </h1>
            {document.description && <p className="text-slate-600">{document.description}</p>}
            <div className="mt-4 flex gap-6 text-sm text-slate-500">
              <span>Published: {formatDocumentDate(document.updated_at)}</span>
              {selectedVersion && <span>Version: {versionLabel(selectedVersion)}</span>}
            </div>
          </div>

          <div className="prose prose-lg mb-8 max-w-none">
            {content ? (
              isHtmlContent ? (
                <div className="document-preview-content">{renderedContent}</div>
              ) : (
                <div className="whitespace-pre-wrap text-slate-700">{content}</div>
              )
            ) : (
              <p className="italic text-slate-400">No content available.</p>
            )}
          </div>

          {effectiveAttachments.length > 0 && (
            <div className="mt-8 border-t border-slate-200 pt-4">
              <h2 className="mb-2 text-lg font-display font-semibold">Attachments</h2>
              <ul className="list-inside list-disc text-sm text-slate-600">
                {effectiveAttachments.map((attachment) => (
                  <li key={attachment.id}>
                    {attachment.filename} ({formatFileSize(attachment.file_size)})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div
      className={
        isFullscreen
          ? 'fixed inset-0 animate-fade-in bg-white dark:bg-slate-950'
          : 'min-h-screen animate-fade-in bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900'
      }
    >
      {!isFullscreen ? (
        <Header />
      ) : (
        <div className="flex items-center justify-between gap-4 bg-gradient-to-l from-blue-700 via-blue-600 to-blue-500 px-4 py-3 text-white shadow-lg">
          <button
            onClick={() => {
              const params = new URLSearchParams(location.search)
              params.delete('fullscreen')
              navigate(`/viewer/documents/${id}${params.toString() ? `?${params.toString()}` : ''}`)
            }}
            className="rounded-lg bg-white/20 px-3 py-1.5 transition-colors hover:bg-white/30"
            type="button"
          >
            Exit Fullscreen
          </button>
          <div className="flex-1 truncate text-center font-display font-semibold">{document.title}</div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => applyWidth('reading')}
              className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                contentWidth === 'reading'
                  ? 'border-white bg-white text-blue-900'
                  : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
              }`}
              type="button"
            >
              Reading width
            </button>
            <button
              onClick={() => applyWidth('fluid')}
              className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                contentWidth === 'fluid'
                  ? 'border-white bg-white text-blue-900'
                  : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
              }`}
              type="button"
            >
              Full width
            </button>
          </div>
        </div>
      )}

      <main
        className={`${contentWidth === 'reading' ? 'reading-mode' : ''} ${
          isFullscreen
            ? `h-[calc(100vh-56px)] w-full overflow-y-auto ${contentWidth === 'reading' ? 'mx-auto max-w-4xl' : 'max-w-none'} px-6 md:px-10 lg:px-16`
            : `${contentWidth === 'reading' ? 'content-shell max-w-4xl' : 'px-6 md:px-10 lg:px-16'}`
        } py-8`}
      >
        <nav className="mb-6 flex items-center justify-between">
          <Link to="/viewer" className="body-copy text-blue-600 hover:underline">
            Documents
          </Link>
          <div className="flex items-center gap-2">
            <span className="helper-copy">/</span>
            <span className="body-copy text-slate-600 dark:text-slate-300">{document.title}</span>
          </div>
          {!isFullscreen && (
            <button
              onClick={() => {
                const params = new URLSearchParams(location.search)
                params.set('fullscreen', '1')
                navigate(`/viewer/documents/${id}?${params.toString()}`)
              }}
              className="btn-ghost table-action-btn"
              type="button"
            >
              Fullscreen
            </button>
          )}
        </nav>

        <div className="surface-card mb-6 rounded-2xl p-8">
          <div className="mb-4 flex items-start justify-between">
            <span className="pill border-blue-200 bg-blue-100 text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-200">
              {document.category || 'General'}
            </span>
            <span className="font-mono text-sm text-slate-400 dark:text-slate-500">
              {document.document_number}
            </span>
          </div>

          <h1 className="mb-4 text-3xl font-display font-bold text-slate-900 dark:text-slate-100">
            {document.title}
          </h1>

          {document.description && (
            <p className="body-copy mb-6 text-base">{document.description}</p>
          )}

          <div className="helper-copy flex flex-wrap gap-6 border-t border-slate-200 pt-4 dark:border-slate-800">
            <div>
              <span className="font-medium text-slate-700 dark:text-slate-200">Published:</span>{' '}
              {formatDocumentDate(document.updated_at)}
            </div>
            {selectedVersion && (
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-200">Version:</span>{' '}
                {versionLabel(selectedVersion)}
              </div>
            )}
            <div className="ml-auto flex gap-2">
              <button onClick={() => setIsPrintMode(true)} className="btn-ghost table-action-btn" type="button">
                Print View
              </button>
            </div>
          </div>
        </div>

        <div className="surface-card mb-6 rounded-2xl p-8">
          <h2 className="section-title mb-4">Content</h2>
          <div className="max-w-none">
            {!selectedVersion ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center dark:border-slate-800 dark:bg-slate-950">
                <p className="card-title text-slate-700 dark:text-slate-200">No published versions available.</p>
                <p className="body-copy mt-1">
                  This document has no versions to display.
                </p>
              </div>
            ) : selectedVersionAttachmentsLoading ? (
              <div className="flex h-[40vh] items-center justify-center">
                <div className="body-copy text-center">
                  <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-b-2 border-blue-600"></div>
                  Loading version content...
                </div>
              </div>
            ) : content ? (
              isHtmlContent ? (
                <div className={documentPaperClass}>
                  <div className="document-preview-content">{renderedContent}</div>
                </div>
              ) : (
                <div className="prose prose-lg max-w-none dark:prose-invert">
                  <div className="whitespace-pre-wrap text-slate-700 dark:text-slate-300">{content}</div>
                </div>
              )
            ) : effectiveAttachments.length > 0 ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center dark:border-amber-900 dark:bg-amber-950/40">
                <p className="card-title text-amber-900 dark:text-amber-200">
                  No inline preview is available for the selected version.
                </p>
                <p className="body-copy mt-1 text-amber-800 dark:text-amber-300">
                  Download one of the attached files below to view the original document.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center dark:border-slate-800 dark:bg-slate-950">
                <p className="card-title text-slate-700 dark:text-slate-200">No content available for this version.</p>
              </div>
            )}
          </div>
        </div>

        {effectiveAttachments.length > 0 && (
          <div className="surface-card mb-6 rounded-2xl p-8">
            <h2 className="section-title mb-4">
              Attachments ({effectiveAttachments.length})
            </h2>
            <div className="space-y-3">
              {effectiveAttachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between rounded-xl bg-slate-50 p-4 transition-colors hover:bg-slate-100 dark:bg-slate-950 dark:hover:bg-slate-900"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getFileIcon(attachment.mime_type)}</span>
                    <div>
                      <p className="card-title">{attachment.filename}</p>
                      <p className="body-copy">
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
                    className="btn-primary table-action-btn"
                  >
                    Download
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {versions.length > 0 && (
          <div className="surface-card mb-6 rounded-2xl p-8">
            <h2 className="section-title mb-4">
              Version History ({versions.length})
            </h2>
            <div className="space-y-3">
              {versions.map((version) => (
                <button
                  key={version.id}
                  type="button"
                  onClick={() => handleVersionSelect(version.id)}
                  className={`w-full rounded-xl border p-4 text-left transition-colors hover:border-blue-300 dark:hover:border-blue-700 ${
                    selectedVersionId === version.id
                      ? 'border-blue-400 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/40'
                      : version.is_published
                        ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30'
                        : 'border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-medium text-slate-900 dark:text-slate-100">
                        v{versionLabel(version)}
                      </span>
                      {selectedVersionId === version.id && (
                        <span className="pill border-blue-200 bg-blue-100 text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-200">
                          Viewing
                        </span>
                      )}
                      {version.is_published && (
                        <span className="pill border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200">
                          Published
                        </span>
                      )}
                    </div>
                    <span className="body-copy">
                      {formatDocumentDate(version.created_at)}
                    </span>
                  </div>
                  {version.changes_summary && (
                    <p className="body-copy mt-2">
                      {version.changes_summary}
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="pt-4 text-center">
          <Link to="/viewer" className="btn-ghost table-action-btn inline-flex">
            Back to All Documents
          </Link>
        </div>
      </main>
    </div>
  )
}

function Header() {
  return (
    <header className="border-b border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="content-shell py-6">
        <div className="flex items-center justify-between">
          <Link to="/viewer" className="flex items-center gap-2">
            <h1 className="text-2xl font-display font-bold text-slate-900 dark:text-slate-100">
              Documentation Platform
            </h1>
          </Link>
          <Link
            to="/login"
            className="btn-secondary table-action-btn"
          >
            Staff Login
          </Link>
        </div>
      </div>
    </header>
  )
}

function getFileIcon(mimeType: string): string {
  if (mimeType?.startsWith('image/')) return 'IMG'
  if (mimeType?.includes('presentation')) return 'PPT'
  if (mimeType?.includes('word') || mimeType?.includes('document')) return 'DOC'
  if (mimeType?.includes('excel') || mimeType?.includes('spreadsheet')) return 'XLS'
  if (mimeType?.includes('zip') || mimeType?.includes('archive')) return 'ZIP'
  return 'FILE'
}

function formatFileSize(bytes: number): string {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
