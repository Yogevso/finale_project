import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

export default function ViewerDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const [isPrintMode, setIsPrintMode] = useState(false)

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
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-white rounded-xl shadow-sm border p-8 animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-100 rounded w-1/4 mb-8"></div>
            <div className="space-y-3">
              <div className="h-4 bg-gray-100 rounded w-full"></div>
              <div className="h-4 bg-gray-100 rounded w-full"></div>
              <div className="h-4 bg-gray-100 rounded w-2/3"></div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-16 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Document Not Found
          </h1>
          <p className="text-gray-500 mb-6">
            The document you're looking for doesn't exist or is not published.
          </p>
          <Link
            to="/viewer"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            ← Back to Documents
          </Link>
        </main>
      </div>
    )
  }

  // Get the latest published version content
  const latestVersion = versions.find((v: any) => v.is_published)
  const content = latestVersion?.content || document.content || ''

  // Print-friendly view
  if (isPrintMode) {
    return (
      <div className="min-h-screen bg-white print:bg-white">
        {/* Print Header - hidden when printing */}
        <div className="print:hidden bg-gray-100 p-4 flex items-center justify-between">
          <button
            onClick={() => setIsPrintMode(false)}
            className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-white"
          >
            ← Back to Document
          </button>
          <button
            onClick={() => window.print()}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            🖨️ Print Document
          </button>
        </div>

        {/* Printable Content */}
        <div className="max-w-3xl mx-auto p-8 print:p-0 print:max-w-none">
          {/* Document Header */}
          <div className="border-b-2 border-gray-300 pb-4 mb-6">
            <div className="flex justify-between text-sm text-gray-500 mb-2">
              <span>{document.document_number}</span>
              <span>{document.category || 'General'}</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {document.title}
            </h1>
            {document.description && (
              <p className="text-gray-600">{document.description}</p>
            )}
            <div className="mt-4 text-sm text-gray-500 flex gap-6">
              <span>Published: {new Date(document.updated_at).toLocaleDateString()}</span>
              {latestVersion && <span>Version: {latestVersion.version_number}</span>}
            </div>
          </div>

          {/* Content */}
          <div className="prose prose-lg max-w-none mb-8">
            <div className="whitespace-pre-wrap text-gray-700">{content}</div>
          </div>

          {/* Attachments List */}
          {attachments.length > 0 && (
            <div className="border-t border-gray-200 pt-4 mt-8">
              <h2 className="text-lg font-semibold mb-2">Attachments</h2>
              <ul className="list-disc list-inside text-sm text-gray-600">
                {attachments.map((a: any) => (
                  <li key={a.id}>{a.filename} ({formatFileSize(a.file_size)})</li>
                ))}
              </ul>
            </div>
          )}

          {/* Print Footer */}
          <div className="border-t border-gray-200 pt-4 mt-8 text-xs text-gray-400 print:block">
            <p>Printed from Document Portal • {new Date().toLocaleDateString()}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <Header />

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <nav className="mb-6 text-sm">
          <Link to="/viewer" className="text-blue-600 hover:underline">
            Documents
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-gray-600">{document.title}</span>
        </nav>

        {/* Document Header */}
        <div className="bg-white rounded-xl shadow-sm border p-8 mb-6">
          <div className="flex items-start justify-between mb-4">
            <span className="text-sm font-medium text-blue-600 bg-blue-50 px-3 py-1 rounded-full">
              {document.category || 'General'}
            </span>
            <span className="text-sm text-gray-400 font-mono">
              {document.document_number}
            </span>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {document.title}
          </h1>

          {document.description && (
            <p className="text-lg text-gray-600 mb-6">{document.description}</p>
          )}

          <div className="flex flex-wrap gap-6 text-sm text-gray-500 border-t pt-4">
            <div>
              <span className="font-medium text-gray-700">Published:</span>{' '}
              {new Date(document.updated_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
            {latestVersion && (
              <div>
                <span className="font-medium text-gray-700">Version:</span>{' '}
                {latestVersion.version_number}
              </div>
            )}
            <div className="ml-auto flex gap-2">
              <button
                onClick={() => setIsPrintMode(true)}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 flex items-center gap-1"
              >
                🖨️ Print View
              </button>
            </div>
          </div>
        </div>

        {/* Document Content */}
        <div className="bg-white rounded-xl shadow-sm border p-8 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            📄 Content
          </h2>
          <div className="prose prose-lg max-w-none">
            {content ? (
              <div className="whitespace-pre-wrap text-gray-700">{content}</div>
            ) : (
              <p className="text-gray-400 italic">No content available.</p>
            )}
          </div>
        </div>

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border p-8 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              📎 Attachments
              <span className="text-sm font-normal text-gray-400">
                ({attachments.length})
              </span>
            </h2>
            <div className="space-y-3">
              {attachments.map((attachment: any) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">
                      {getFileIcon(attachment.mime_type)}
                    </span>
                    <div>
                      <p className="font-medium text-gray-900">
                        {attachment.filename}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(attachment.file_size)}
                      </p>
                    </div>
                  </div>
                  <a
                    href={`/api/v1/attachments/${attachment.id}/download`}
                    className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
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
          <div className="bg-white rounded-xl shadow-sm border p-8 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              📋 Version History
              <span className="text-sm font-normal text-gray-400">
                ({versions.length})
              </span>
            </h2>
            <div className="space-y-3">
              {versions.map((version: any) => (
                <div
                  key={version.id}
                  className={`p-4 rounded-lg border ${
                    version.is_published
                      ? 'border-green-200 bg-green-50'
                      : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-medium text-gray-900">
                        v{version.version_number}
                      </span>
                      {version.is_published && (
                        <span className="text-xs font-medium text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                          Published
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-gray-500">
                      {new Date(version.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {version.change_notes && (
                    <p className="text-sm text-gray-600 mt-2">
                      {version.change_notes}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Comments */}
        {comments.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border p-8 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              💬 Comments
              <span className="text-sm font-normal text-gray-400">
                ({comments.length})
              </span>
            </h2>
            <div className="space-y-4">
              {comments.map((comment: any) => (
                <div
                  key={comment.id}
                  className="p-4 bg-gray-50 rounded-lg border-l-4 border-blue-200"
                >
                  <p className="text-gray-700 mb-2">{comment.content}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
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
            className="inline-block px-6 py-3 border border-gray-300 rounded-lg hover:bg-white transition-colors"
          >
            ← Back to All Documents
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 py-8 text-center text-gray-500 text-sm">
          <p>Document Portal V2 • Built with React + FastAPI</p>
        </div>
      </footer>
    </div>
  )
}

function Header() {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <Link to="/viewer" className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">📚 Document Portal</h1>
          </Link>
          <Link
            to="/login"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
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
