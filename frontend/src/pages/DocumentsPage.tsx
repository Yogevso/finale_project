import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import VisibilityBadge from '@/components/VisibilityBadge'
import RichTextEditor from '@/components/RichTextEditor'
import PageHeader from '@/components/PageHeader'
import type { DocumentStatus, DocumentVisibility, DocumentCreate } from '@/types'

export default function DocumentsPage() {
  const { isEditor, isManager } = useAuth()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | ''>('')
  const [visibilityFilter, setVisibilityFilter] = useState<DocumentVisibility | ''>('')
  const statusDetailsRef = useRef<HTMLDetailsElement | null>(null)
  const visibilityDetailsRef = useRef<HTMLDetailsElement | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showQuickStartModal, setShowQuickStartModal] = useState(false)
  const [visibilityOverrides, setVisibilityOverrides] = useState<Record<number, DocumentVisibility>>({})
  const action = searchParams.get('action')
  const isQuickCreateMode = action === 'create'

  useEffect(() => {
    if (isQuickCreateMode) {
      setShowQuickStartModal(true)
    }
  }, [isQuickCreateMode])

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.documents.list({
      page,
      page_size: 10,
      search: search || undefined,
      status: statusFilter || undefined,
      visibility: visibilityFilter || undefined,
    }),
    queryFn: () =>
      api.getDocuments({
        page,
        page_size: 10,
        search: search || undefined,
        status: statusFilter || undefined,
        visibility: visibilityFilter || undefined,
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      console.error('Delete error:', error)
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to delete document. You may need Manager or Admin role.')
    },
  })

  const visibilityMutation = useMutation({
    mutationFn: ({ id, visibility }: { id: number; visibility: DocumentVisibility }) =>
      api.updateDocument(id, { visibility }),
    onSuccess: (_, variables) => {
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown, variables) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to update visibility.')
    },
  })

  const handleDelete = (id: number, title: string) => {
    if (!isManager) {
      return
    }
    if (confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id)
    }
  }
  const totalDocuments = data?.total ?? 0

  return (
    <div className="space-y-8">
      <PageHeader
        title="Documents"
        subtitle="Manage all documents"
        actions={
          isEditor ? (
            <>
              <button
                onClick={() => setShowUploadModal(true)}
                className="btn-secondary flex items-center gap-2"
              >
                <span>📤</span> Upload File
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="btn-primary"
              >
                + New Document
              </button>
            </>
          ) : undefined
        }
      />

      {!isQuickCreateMode && (
        <div className="admin-sticky-toolbar">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="inline-flex items-center gap-2 text-sm text-slate-600">
              <span className="admin-summary-badge">
                {isLoading ? 'Loading...' : `${totalDocuments} total`}
              </span>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
              <div className="relative w-full sm:w-72">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input-field pl-9"
                />
              </div>
              <div className="flex flex-wrap gap-2 sm:justify-end">
                <details ref={statusDetailsRef} className="relative">
                  <summary className="list-none cursor-pointer whitespace-nowrap px-3 py-2 rounded-full border border-slate-200 bg-white text-sm text-slate-600 hover:bg-slate-50">
                    Status: {
                      statusFilter === 'active'
                        ? 'Published'
                        : statusFilter === 'approved'
                        ? 'Approved'
                        : statusFilter || 'All'
                    }
                  </summary>
                  <div className="absolute right-0 mt-2 w-44 rounded-xl border border-slate-200 bg-white shadow-lg p-2 z-10">
                    {[
                      { label: 'All', value: '' },
                      { label: 'Draft', value: 'draft' },
                      { label: 'Pending Review', value: 'pending_review' },
                      { label: 'Approved', value: 'approved' },
                      { label: 'Published', value: 'active' },
                      { label: 'Archived', value: 'archived' },
                    ].map((item) => (
                      <button
                        key={item.label}
                        type="button"
                        onClick={() => {
                          setStatusFilter(item.value as DocumentStatus | '')
                          statusDetailsRef.current?.removeAttribute('open')
                        }}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-slate-100 ${
                          statusFilter === item.value ? 'bg-slate-100 text-slate-900' : 'text-slate-600'
                        }`}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </details>

                <details ref={visibilityDetailsRef} className="relative">
                  <summary className="list-none cursor-pointer whitespace-nowrap px-3 py-2 rounded-full border border-slate-200 bg-white text-sm text-slate-600 hover:bg-slate-50">
                    Visibility: {visibilityFilter || 'All'}
                  </summary>
                  <div className="absolute right-0 mt-2 w-40 rounded-xl border border-slate-200 bg-white shadow-lg p-2 z-10">
                    {[
                      { label: 'All', value: '' },
                      { label: 'Public', value: 'public' },
                      { label: 'Internal', value: 'internal' },
                      { label: 'Company', value: 'company' },
                    ].map((item) => (
                      <button
                        key={item.label}
                        type="button"
                        onClick={() => {
                          setVisibilityFilter(item.value as DocumentVisibility | '')
                          visibilityDetailsRef.current?.removeAttribute('open')
                        }}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-slate-100 ${
                          visibilityFilter === item.value ? 'bg-slate-100 text-slate-900' : 'text-slate-600'
                        }`}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </details>
              </div>
            </div>
          </div>
        </div>
      )}

      {isQuickCreateMode && (
        <div className="surface-card rounded-2xl p-6">
          <h2 className="text-lg font-display font-semibold text-slate-900 mb-2">
            Create a new document
          </h2>
          <p className="text-sm text-slate-500 mb-6">
            Choose how you want to start.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => setShowCreateModal(true)}
              className="surface-card-hover rounded-2xl p-6 text-left"
            >
              <div className="text-3xl mb-3">📝</div>
              <div className="text-lg font-display font-semibold text-slate-900">New Document</div>
              <p className="text-sm text-slate-500 mt-2">
                Start from a blank document and add content.
              </p>
            </button>
            <button
              onClick={() => setShowUploadModal(true)}
              className="surface-card-hover rounded-2xl p-6 text-left"
            >
              <div className="text-3xl mb-3">📤</div>
              <div className="text-lg font-display font-semibold text-slate-900">Upload File</div>
              <p className="text-sm text-slate-500 mt-2">
                Upload a PDF or Word file and generate a document.
              </p>
            </button>
          </div>
        </div>
      )}

      {!isQuickCreateMode && (
        <div className="admin-table-shell">
          <div className="admin-table-scroll">
            <table className="admin-table">
              <thead className="admin-table-head">
                <tr>
                  <th className="w-[40%]">Document</th>
                  <th className="w-[14%]">Status</th>
                  <th>Visibility</th>
                  <th>Category</th>
                  <th>Created</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr className="admin-table-row">
                    <td colSpan={6} className="px-5 py-10 text-center text-slate-500">
                      Loading...
                    </td>
                  </tr>
                ) : data?.items.length === 0 ? (
                  <tr className="admin-table-row">
                    <td colSpan={6} className="px-5 py-10 text-center text-slate-500">
                      No documents found
                    </td>
                  </tr>
                ) : (
                  data?.items.map((doc) => (
                    <tr key={doc.id} className="admin-table-row">
                      <td className="admin-table-cell w-[40%]">
                        <a
                          href={`/documents/${doc.id}/fullscreen`}
                          className="block hover:text-sky-700"
                        >
                          <div className="font-medium text-slate-900">{doc.title}</div>
                          <div className="text-sm text-slate-500">{doc.document_number}</div>
                        </a>
                      </td>
                      <td className="admin-table-cell w-[14%]">
                        <span
                          className={`pill whitespace-nowrap ${
                            doc.status === 'active'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : doc.status === 'approved'
                              ? 'bg-sky-50 text-sky-700 border-sky-200'
                              : doc.status === 'draft'
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : doc.status === 'pending_review'
                              ? 'bg-purple-50 text-purple-700 border-purple-200'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                          }`}
                        >
                          {doc.status === 'active'
                            ? 'Published'
                            : doc.status === 'approved'
                            ? 'Approved'
                            : doc.status}
                        </span>
                      </td>
                      <td className="admin-table-cell">
                        {isManager ? (
                          <select
                            value={visibilityOverrides[doc.id] || doc.visibility || 'internal'}
                            onChange={(e) => {
                              const nextVisibility = e.target.value as DocumentVisibility
                              setVisibilityOverrides((prev) => ({ ...prev, [doc.id]: nextVisibility }))
                              visibilityMutation.mutate({ id: doc.id, visibility: nextVisibility })
                            }}
                            className="select-field w-40 min-w-[9.5rem]"
                          >
                            <option value="internal">Internal</option>
                            <option value="public">Public</option>
                            <option value="company">Company</option>
                          </select>
                        ) : (
                          <VisibilityBadge visibility={doc.visibility || 'internal'} size="sm" />
                        )}
                      </td>
                      <td className="admin-table-cell text-slate-500">{doc.category || '-'}</td>
                      <td className="admin-table-cell text-slate-500 whitespace-nowrap">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="admin-table-cell text-right whitespace-nowrap">
                        {isManager ? (
                          <button
                            onClick={() => handleDelete(doc.id, doc.title)}
                            className="text-rose-600 hover:text-rose-700 font-semibold text-xs uppercase tracking-wide"
                          >
                            Delete
                          </button>
                        ) : (
                          <span className="text-slate-400 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {data && data.pages > 1 && (
            <div className="px-5 py-4 border-t border-slate-200 flex items-center justify-between">
              <div className="text-sm text-slate-500">
                Page {data.page} of {data.pages} ({data.total} total)
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-ghost disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                  disabled={page === data.pages}
                  className="btn-ghost disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateDocumentModal onClose={() => setShowCreateModal(false)} />
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadDocumentModal onClose={() => setShowUploadModal(false)} />
      )}

      {showQuickStartModal && (
        <QuickStartModal
          onClose={() => setShowQuickStartModal(false)}
          onCreate={() => {
            setShowQuickStartModal(false)
            setShowCreateModal(true)
          }}
          onUpload={() => {
            setShowQuickStartModal(false)
            setShowUploadModal(true)
          }}
        />
      )}
    </div>
  )
}

function CreateDocumentModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [formData, setFormData] = useState<DocumentCreate & { content?: string }>({
    title: '',
    description: '',
    status: 'draft',
    visibility: 'internal',
    category: '',
    release_branch: '',
    tags: '',
    content: '',
  })
  const [error, setError] = useState('')
  const [generateWord, setGenerateWord] = useState(false)

  const createMutation = useMutation({
    mutationFn: async (data: DocumentCreate & { content?: string }) => {
      // First create the document
      const doc = await api.createDocument({
        title: data.title,
        description: data.description,
        status: 'draft',
        visibility: 'internal',
        category: data.category,
        release_branch: data.release_branch,
        tags: data.tags,
      })
      // If there's content, create a version with it
      if (data.content && data.content.trim()) {
        await api.createVersion(doc.id, {
          content: data.content,
          changes_summary: 'Initial content',
        })
        // Publishing is now a separate step that requires an approved review.
        if (generateWord) {
          await api.generateWordAttachment(doc.id, data.content, `${data.title}.docx`)
        }
      } else if (generateWord) {
        throw new Error('Please add content before generating a Word file')
      }
      return doc
    },
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      onClose()
      // Navigate to fullscreen view to continue editing
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to create document')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim()) {
      setError('Title is required')
      return
    }
    createMutation.mutate(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h2 className="text-xl font-display font-bold text-slate-900">Create Document</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-xl text-slate-500"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
          {error && (
            <div className="mx-4 mt-4 p-3 bg-rose-50 text-rose-700 rounded-xl text-sm">{error}</div>
          )}

          <div className="flex-1 flex overflow-hidden">
            {/* Left side - Document details */}
            <div className="w-80 p-4 border-r border-slate-200 overflow-y-auto space-y-4 surface-muted">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input-field"
                  placeholder="Enter document title"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input-field"
                  rows={2}
                  placeholder="Brief description"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
                <input
                  type="text"
                  value="Draft"
                  disabled
                  className="input-field disabled:opacity-70"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Visibility</label>
                <input
                  type="text"
                  value="Internal"
                  disabled
                  className="input-field disabled:opacity-70"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="input-field"
                  placeholder="e.g., Policy, Guide"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Release Branch</label>
                <input
                  type="text"
                  value={formData.release_branch || ''}
                  onChange={(e) => setFormData({ ...formData, release_branch: e.target.value })}
                  className="input-field"
                  placeholder="e.g., R580"
                />
              </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
              <input
                type="text"
                value={formData.tags}
                onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                className="input-field"
                placeholder="Comma-separated"
              />
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={generateWord}
                  onChange={(e) => setGenerateWord(e.target.checked)}
                  className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                />
                Generate Word file (DOCX)
              </label>
              <p className="text-xs text-slate-400 mt-1">
                Creates a Word attachment from the editor content.
              </p>
            </div>
          </div>

            {/* Right side - Content editor */}
              <div className="flex-1 p-4 flex flex-col overflow-hidden min-h-0">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Content <span className="text-slate-400 font-normal">(start typing your document)</span>
                </label>
                <div className="flex-1 min-h-0">
                  <RichTextEditor
                    content={formData.content || ''}
                    onChange={(html) => setFormData({ ...formData, content: html })}
                    editable={true}
                    scrollable
                    className="h-full"
                  />
                </div>
              </div>
          </div>

          <div className="flex justify-end gap-3 p-4 border-t border-slate-200 surface-muted">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Creating...
                </>
              ) : (
                'Create & Continue Editing'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
function UploadDocumentModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [releaseBranch, setReleaseBranch] = useState('')
  const [tags, setTags] = useState('')
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const allowedMimeTypes = new Set([
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ])
  const allowedExtensions = new Set([
    '.pdf',
    '.doc',
    '.docx',
  ])
  const acceptedFileTypes = '.pdf,.doc,.docx'

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      api.uploadDocument(file, {
        title: title || undefined,
        description: description || undefined,
        category: category || undefined,
        release_branch: releaseBranch || undefined,
        tags: tags || undefined,
      }),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      onClose()
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to upload document')
    },
  })

  const handleFileSelect = (file: File) => {
    const mime = (file.type || '').toLowerCase()
    const extensionMatch = file.name.toLowerCase().match(/\.[^.]+$/)
    const extension = extensionMatch ? extensionMatch[0] : ''
    const isSupported = allowedMimeTypes.has(mime) || allowedExtensions.has(extension)

    if (!isSupported) {
      setError('Only PDF and Word documents are allowed')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB')
      return
    }

    setSelectedFile(file)
    setError('')
    if (!title) {
      setTitle(file.name.replace(/\.[^/.]+$/, ''))
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setError('Please select a file to upload')
      return
    }
    uploadMutation.mutate(selectedFile)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-display font-bold text-slate-900 mb-4">Upload Document</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 text-rose-700 rounded-xl text-sm">{error}</div>
          )}

          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              dragActive ? 'border-sky-500 bg-sky-50' : 'border-slate-300 hover:border-slate-400'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={acceptedFileTypes}
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            />
            {selectedFile ? (
              <div>
                <span className="text-3xl">📄</span>
                <p className="mt-2 font-medium text-slate-900">{selectedFile.name}</p>
                <p className="text-sm text-slate-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div>
                <span className="text-3xl">📤</span>
                <p className="mt-2 text-slate-600">Drag & drop a file here, or click to browse</p>
                <p className="text-sm text-slate-400 mt-1">PDF, DOC, DOCX (max 10MB)</p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input-field"
              placeholder="Document title (uses filename if empty)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field"
              rows={2}
              placeholder="Optional description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input-field"
                placeholder="e.g., Reports"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="input-field"
                placeholder="tag1, tag2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Release Branch</label>
            <input
              type="text"
              value={releaseBranch}
              onChange={(e) => setReleaseBranch(e.target.value)}
              className="input-field"
              placeholder="e.g., R580"
            />
          </div>


          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="btn-primary disabled:opacity-50"
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function QuickStartModal({
  onClose,
  onCreate,
  onUpload,
}: {
  onClose: () => void
  onCreate: () => void
  onUpload: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-display font-bold text-slate-900">Start a new document</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-xl text-slate-500"
          >
            ✕
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-6">
          Choose how you want to create your document.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={onCreate}
            className="surface-card-hover rounded-2xl p-6 text-left"
          >
            <div className="text-3xl mb-3">📝</div>
            <div className="text-lg font-display font-semibold text-slate-900">New Document</div>
            <p className="text-sm text-slate-500 mt-2">
              Start from a blank document and add content.
            </p>
          </button>
          <button
            onClick={onUpload}
            className="surface-card-hover rounded-2xl p-6 text-left"
          >
            <div className="text-3xl mb-3">📤</div>
            <div className="text-lg font-display font-semibold text-slate-900">Upload File</div>
            <p className="text-sm text-slate-500 mt-2">
              Upload a PDF or Word file and generate a document.
            </p>
          </button>
        </div>
      </div>
    </div>
  )
}
