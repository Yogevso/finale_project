/**
 * CustomerDocumentPage - Document detail view for customer portal
 */
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portalApi } from '../../lib/portalApi'
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
  const queryClient = useQueryClient()
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)

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

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="text-center py-12 bg-white rounded-lg shadow">
        <FileText className="h-16 w-16 mx-auto text-gray-300" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">Document not found</h3>
        <p className="mt-2 text-gray-500">
          This document may not exist or you don't have access to view it.
        </p>
        <Link
          to="/portal/documents"
          className="mt-4 inline-flex items-center text-indigo-600 hover:text-indigo-500"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Documents
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Link
        to="/portal/documents"
        className="inline-flex items-center text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Documents
      </Link>

      {/* Document header */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{document.title}</h1>
              {document.description && (
                <p className="mt-2 text-gray-600">{document.description}</p>
              )}
            </div>
            <span className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">
              v{document.version}
            </span>
          </div>

          {/* Metadata */}
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500">
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
              <Tag className="h-4 w-4 text-gray-400" />
              {document.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 bg-gray-100 text-gray-600 text-sm rounded"
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
            className="prose max-w-none"
            dangerouslySetInnerHTML={{ __html: document.content }}
          />
        </div>
      </div>

      {/* Attachments */}
      {document.attachments.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <Paperclip className="h-5 w-5 mr-2" />
              Attachments ({document.attachments.length})
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {document.attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center min-w-0">
                    <FileText className="h-8 w-8 text-gray-400 flex-shrink-0" />
                    <div className="ml-3 min-w-0">
                      <p className="font-medium text-gray-900 truncate">{attachment.filename}</p>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(attachment.file_size)}
                        {attachment.mime_type && ` • ${attachment.mime_type}`}
                      </p>
                    </div>
                  </div>
                  <a
                    href={`/api/v1/attachments/${attachment.id}/download`}
                    className="ml-4 flex items-center px-3 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
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
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Submit Feedback</h2>
          <p className="text-sm text-gray-500">
            Have a question or suggestion about this document? Let us know!
          </p>
        </div>
        <div className="p-6">
          {feedbackSubmitted ? (
            <div className="text-center py-8">
              <CheckCircle className="h-12 w-12 mx-auto text-green-500" />
              <h3 className="mt-4 font-medium text-gray-900">Thank you for your feedback!</h3>
              <p className="mt-2 text-gray-500">
                We've received your submission and will respond soon.
              </p>
              <div className="mt-4 flex justify-center gap-4">
                <button
                  onClick={() => setFeedbackSubmitted(false)}
                  className="text-indigo-600 hover:text-indigo-500"
                >
                  Submit another
                </button>
                <Link to="/portal/feedback" className="text-indigo-600 hover:text-indigo-500">
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
  )
}
