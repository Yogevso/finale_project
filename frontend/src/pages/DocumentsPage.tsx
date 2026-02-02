import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import VisibilityBadge from '@/components/VisibilityBadge'
import RichTextEditor from '@/components/RichTextEditor'
import type { DocumentStatus, DocumentVisibility, DocumentCreate } from '@/types'

export default function DocumentsPage() {
  const { isEditor, isManager } = useAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | ''>('')
  const [visibilityFilter, setVisibilityFilter] = useState<DocumentVisibility | ''>('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [visibilityOverrides, setVisibilityOverrides] = useState<Record<number, DocumentVisibility>>({})

  const { data, isLoading } = useQuery({
    queryKey: ['documents', page, search, statusFilter],
    queryFn: () =>
      api.getDocuments({
        page,
        page_size: 10,
        search: search || undefined,
        status: statusFilter || undefined,
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error: any) => {
      console.error('Delete error:', error)
      alert(error?.response?.data?.detail || error?.message || 'Failed to delete document. You may need Manager or Admin role.')
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
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error: any, variables) => {
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      alert(error?.response?.data?.detail || error?.message || 'Failed to update visibility.')
    },
  })

  const handleDelete = (id: number, title: string) => {
    if (confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Documents</h1>
          <p className="text-slate-500 mt-1">Manage all documents</p>
        </div>
        {isEditor && (
          <div className="flex gap-3">
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
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Search documents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field flex-1 min-w-[200px]"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as DocumentStatus | '')}
          className="select-field"
        >
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="pending_review">Pending Review</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
        <select
          value={visibilityFilter}
          onChange={(e) => setVisibilityFilter(e.target.value as DocumentVisibility | '')}
          className="select-field"
        >
          <option value="">All Visibility</option>
          <option value="public">Public</option>
          <option value="internal">Internal</option>
          <option value="company">Company</option>
        </select>
      </div>

      {/* Documents Table */}
      <div className="surface-card rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Document</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Visibility</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Created</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  Loading...
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  No documents found
                </td>
              </tr>
            ) : (
              data?.items.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <div>
                      <div className="font-medium text-slate-900">{doc.title}</div>
                      <div className="text-sm text-slate-500">{doc.document_number}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`pill ${
                        doc.status === 'active'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : doc.status === 'draft'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : doc.status === 'pending_review'
                          ? 'bg-purple-50 text-purple-700 border-purple-200'
                          : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {isManager ? (
                      <select
                        value={visibilityOverrides[doc.id] || doc.visibility || 'internal'}
                        onChange={(e) => {
                          const nextVisibility = e.target.value as DocumentVisibility
                          setVisibilityOverrides((prev) => ({ ...prev, [doc.id]: nextVisibility }))
                          visibilityMutation.mutate({ id: doc.id, visibility: nextVisibility })
                        }}
                        className="select-field w-44"
                      >
                        <option value="internal">Internal</option>
                        <option value="public">Public</option>
                        <option value="company">Company</option>
                      </select>
                    ) : (
                      <VisibilityBadge visibility={doc.visibility || 'internal'} size="sm" />
                    )}
                  </td>
                  <td className="px-6 py-4 text-slate-500">{doc.category || '-'}</td>
                  <td className="px-6 py-4 text-slate-500">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <a
                      href={`/documents/${doc.id}`}
                      className="text-sky-600 hover:text-sky-800 font-medium"
                    >
                      View
                    </a>
                    {isEditor && (
                      <button
                        onClick={() => handleDelete(doc.id, doc.title)}
                        className="text-rose-500 hover:text-rose-700 font-medium"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-between">
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

      {/* Create Modal */}
      {showCreateModal && (
        <CreateDocumentModal onClose={() => setShowCreateModal(false)} />
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadDocumentModal onClose={() => setShowUploadModal(false)} />
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
    tags: '',
    content: '',
  })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: async (data: DocumentCreate & { content?: string }) => {
      // First create the document
      const doc = await api.createDocument({
        title: data.title,
        description: data.description,
        status: data.status,
        visibility: data.visibility,
        category: data.category,
        tags: data.tags,
      })
      // If there's content, create a version with it and publish it
      if (data.content && data.content.trim()) {
        const version = await api.createVersion(doc.id, {
          content: data.content,
          changes_summary: 'Initial content',
        })
        // Publish the initial version so it shows in preview
        await api.publishVersion(doc.id, version.id)
      }
      return doc
    },
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      onClose()
      // Navigate to the editor to continue editing
      navigate(`/documents/${doc.id}/edit`)
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
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as DocumentStatus })}
                  className="select-field"
                >
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="archived">Archived</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Visibility</label>
                <select
                  value={formData.visibility}
                  onChange={(e) => setFormData({ ...formData, visibility: e.target.value as DocumentVisibility })}
                  className="select-field"
                >
                  <option value="internal">🏢 Internal</option>
                  <option value="public">🌐 Public</option>
                  <option value="company">🔒 Company</option>
                </select>
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
                <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="input-field"
                  placeholder="Comma-separated"
                />
              </div>
            </div>

            {/* Right side - Content editor */}
            <div className="flex-1 p-4 flex flex-col overflow-hidden">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Content <span className="text-slate-400 font-normal">(start typing your document)</span>
              </label>
              <div className="flex-1 border border-slate-200 rounded-xl overflow-hidden">
                <RichTextEditor
                  content={formData.content || ''}
                  onChange={(html) => setFormData({ ...formData, content: html })}
                  editable={true}
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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadDocument(file, { 
      title: title || undefined, 
      description: description || undefined,
      category: category || undefined,
      tags: tags || undefined
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      onClose()
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to upload document')
    },
  })

  const handleFileSelect = (file: File) => {
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if (!allowedTypes.includes(file.type)) {
      setError('Only PDF and Word documents are allowed')
      return
    }
    
    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB')
      return
    }
    
    setSelectedFile(file)
    setError('')
    // Use filename as default title
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
              accept=".pdf,.doc,.docx"
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
