import { useParams, Link } from 'react-router-dom'
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

export default function PublicDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const documentId = parseInt(id || '0')

  // Fetch document
  const { data: doc, isLoading, error } = useQuery({
    queryKey: ['public-document', documentId],
    queryFn: () => publicApi.getDocument(documentId),
    enabled: documentId > 0,
  })

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
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <FileText className="h-16 w-16 mx-auto mb-4 text-slate-300" />
        <h1 className="text-2xl font-display font-bold text-slate-900 mb-2">Document Not Found</h1>
        <p className="text-slate-500 mb-6">
          This document doesn't exist or is not publicly accessible.
        </p>
        <Link
          to="/browse"
          className="inline-flex items-center gap-2 text-sky-600 hover:text-sky-700 font-medium"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to documents
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        to="/browse"
        className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to documents
      </Link>

      {/* Document Header */}
      <header className="mb-8">
        <div className="flex items-start gap-4">
          <div className="bg-sky-100 rounded-xl p-3">
            <FileText className="h-8 w-8 text-sky-600" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-display font-bold text-slate-900">{doc.title}</h1>
            <p className="text-slate-500 mt-1">{doc.document_number}</p>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap gap-4 mt-6 text-sm text-slate-500">
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

        {/* Tags */}
        {doc.tags && (
          <div className="flex flex-wrap gap-2 mt-4">
            {doc.tags.split(',').map((tag, i) => (
              <span
                key={i}
                className="pill bg-slate-100 text-slate-600 border-slate-200"
              >
                {tag.trim()}
              </span>
            ))}
          </div>
        )}
      </header>

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
            <div 
              dangerouslySetInnerHTML={{ __html: doc.content }}
              className="whitespace-pre-wrap"
            />
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
    </div>
  )
}
