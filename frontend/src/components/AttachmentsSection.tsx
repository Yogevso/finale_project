import { useState, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'
import { useDocumentAttachmentsQuery } from '@/hooks/useDocumentQueries'
import type { Attachment } from '@/types'

interface AttachmentsSectionProps {
  documentId: number
  isEditor: boolean
}

export default function AttachmentsSection({ documentId, isEditor }: AttachmentsSectionProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const { data: attachments = [], isLoading } = useDocumentAttachmentsQuery(documentId)

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      setIsUploading(true)
      setUploadError(null)
      return api.uploadAttachment(documentId, file)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.attachments.byDocument(documentId) })
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    onError: (error: Error) => {
      setUploadError(error.message)
      setIsUploading(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (attachmentId: number) => api.deleteAttachment(documentId, attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.attachments.byDocument(documentId) })
    },
  })

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadMutation.mutate(file)
    }
  }

  const handleDownload = (attachment: Attachment) => {
    const url = api.getAttachmentDownloadUrl(documentId, attachment.id)
    window.open(url, '_blank')
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (mimeType: string): string => {
    if (mimeType.startsWith('image/')) return '🖼️'
    if (mimeType.startsWith('video/')) return '🎬'
    if (mimeType.startsWith('audio/')) return '🎵'
    if (mimeType === 'application/pdf') return '📄'
    if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '📊'
    if (mimeType.includes('document') || mimeType.includes('word')) return '📝'
    if (mimeType.includes('zip') || mimeType.includes('archive')) return '📦'
    return '📎'
  }

  if (isLoading) {
    return <div className="animate-pulse bg-slate-100 h-32 rounded-xl"></div>
  }

  return (
    <div className="surface-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Attachments ({attachments.length})
        </h2>
        {isEditor && (
          <label className="btn-primary text-sm cursor-pointer">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileSelect}
              disabled={isUploading}
            />
            {isUploading ? 'Uploading...' : '+ Upload File'}
          </label>
        )}
      </div>

      {uploadError && (
        <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-700">
          {uploadError}
        </div>
      )}

      {attachments.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-2">📎</div>
          <p className="text-slate-500 text-sm">No attachments yet</p>
          {isEditor && (
            <p className="text-slate-400 text-xs mt-1">Upload files to attach them to this document</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {attachments.map((attachment: Attachment) => (
            <div
              key={attachment.id}
              className="flex items-center justify-between p-3 bg-slate-50 rounded-xl hover:bg-slate-100 group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-2xl">{getFileIcon(attachment.mime_type)}</span>
                <div className="min-w-0">
                  <p className="font-medium text-slate-900 truncate">{attachment.filename}</p>
                  <p className="text-xs text-slate-500">
                    {formatFileSize(attachment.file_size)} • {new Date(attachment.uploaded_at).toLocaleDateString()}
                    {attachment.uploader_name && ` • ${attachment.uploader_name}`}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleDownload(attachment)}
                  className="p-1.5 text-sky-600 hover:bg-sky-50 rounded-lg"
                  title="Download"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </button>
                {isEditor && (
                  <button
                    onClick={() => {
                      if (confirm(`Delete ${attachment.filename}?`)) {
                        deleteMutation.mutate(attachment.id)
                      }
                    }}
                    className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg"
                    title="Delete"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
