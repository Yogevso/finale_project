import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { DocumentUpdate, DocumentStatus, Attachment } from '@/types'
import VersionsSection from '@/components/VersionsSection'
import AttachmentsSection from '@/components/AttachmentsSection'
import CommentsSection from '@/components/CommentsSection'
import EngagementBar from '@/components/EngagementBar'
import DocumentEditor from '@/components/DocumentEditor'
import mammoth from 'mammoth'

type TabType = 'preview' | 'edit-content' | 'details' | 'versions' | 'attachments' | 'comments'

// Type for inline comment anchor
interface PendingAnchor {
  text: string
  id: string
}

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isEditor } = useAuth()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('preview')
  const [scrollProgress, setScrollProgress] = useState<number>(0)
  const [pendingAnchor, setPendingAnchor] = useState<PendingAnchor | null>(null)

  // Callback for DocumentPreview to report scroll progress
  const handleScrollProgress = useCallback((progress: number) => {
    setScrollProgress(progress)
  }, [])

  // Callback when user selects text in preview for inline comment
  const handleTextSelect = useCallback((text: string) => {
    if (text.trim().length >= 5) {
      const anchorId = `anchor-${Date.now()}`
      setPendingAnchor({ text: text.trim(), id: anchorId })
      // Switch to comments tab to show the comment form with anchor
      setActiveTab('comments')
    }
  }, [])

  const { data: document, isLoading, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.getDocument(Number(id)),
    enabled: !!id,
  })

  // Fetch attachments to check if there's a primary document to preview
  const { data: attachments = [] } = useQuery({
    queryKey: ['attachments', id],
    queryFn: () => api.getAttachments(Number(id)),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: (data: DocumentUpdate) => api.updateDocument(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteDocument(Number(id)),
    onSuccess: () => {
      navigate('/documents')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="bg-red-50 text-red-700 p-6 rounded-xl">
        Document not found
      </div>
    )
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate()
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate('/documents')}
            className="text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            ← Back to Documents
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{document.title}</h1>
          <p className="text-gray-500 mt-1">{document.document_number}</p>
        </div>
        {isEditor && (
          <div className="flex gap-2">
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
            <button
              onClick={handleDelete}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {/* Engagement Bar */}
      <EngagementBar documentId={Number(id)} scrollProgress={activeTab === 'preview' ? scrollProgress : undefined} />

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {(['preview', 'edit-content', 'details', 'versions', 'attachments', 'comments'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'preview' ? '📄 Preview' : tab === 'edit-content' ? '✏️ Edit Content' : tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'preview' && (
        <DocumentPreview documentId={Number(id)} attachments={attachments} documentTitle={document.title} onScrollProgress={handleScrollProgress} onTextSelect={handleTextSelect} />
      )}

      {activeTab === 'edit-content' && (
        <DocumentEditor
          documentId={Number(id)}
          attachments={attachments}
          isEditor={isEditor}
          onSave={async (content) => {
            // Save as a new version
            await api.createVersion(Number(id), {
              content,
              changes_summary: 'Edited document content',
            })
            queryClient.invalidateQueries({ queryKey: ['versions', id] })
          }}
        />
      )}

      {activeTab === 'details' && (
        <>
          {isEditing ? (
            <EditForm
              document={document}
              onSave={(data) => updateMutation.mutate(data)}
              onCancel={() => setIsEditing(false)}
              isLoading={updateMutation.isPending}
            />
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="text-sm text-gray-500">Status</label>
                  <p className="mt-1">
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        document.status === 'active'
                          ? 'bg-green-100 text-green-700'
                          : document.status === 'draft'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {document.status}
                    </span>
                  </p>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Category</label>
                  <p className="mt-1 text-gray-900">{document.category || '-'}</p>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Created</label>
                  <p className="mt-1 text-gray-900">
                    {new Date(document.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Updated</label>
                  <p className="mt-1 text-gray-900">
                    {new Date(document.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-500">Description</label>
                <p className="mt-1 text-gray-900 whitespace-pre-wrap">
                  {document.description || 'No description'}
                </p>
              </div>

              {document.tags && (
                <div>
                  <label className="text-sm text-gray-500">Tags</label>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {document.tags.split(',').map((tag, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded"
                      >
                        {tag.trim()}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'versions' && (
        <VersionsSection documentId={Number(id)} isEditor={isEditor} />
      )}

      {activeTab === 'attachments' && (
        <AttachmentsSection documentId={Number(id)} isEditor={isEditor} />
      )}

      {activeTab === 'comments' && (
        <CommentsSection documentId={Number(id)} pendingAnchor={pendingAnchor} onClearAnchor={() => setPendingAnchor(null)} />
      )}
    </div>
  )
}

function EditForm({
  document,
  onSave,
  onCancel,
  isLoading,
}: {
  document: { title: string; description?: string | null; status: DocumentStatus; category?: string | null; tags?: string | null }
  onSave: (data: DocumentUpdate) => void
  onCancel: () => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState<DocumentUpdate>({
    title: document.title,
    description: document.description || '',
    status: document.status as DocumentStatus,
    category: document.category || '',
    tags: document.tags || '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          rows={4}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select
            value={formData.status}
            onChange={(e) => setFormData({ ...formData, status: e.target.value as DocumentStatus })}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <input
            type="text"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
        <input
          type="text"
          value={formData.tags}
          onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          placeholder="Comma-separated tags"
        />
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}
// Document Preview Component
function DocumentPreview({ documentId, attachments, documentTitle, onScrollProgress, onTextSelect }: { documentId: number; attachments: Attachment[]; documentTitle?: string; onScrollProgress?: (progress: number) => void; onTextSelect?: (text: string) => void }) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tableOfContents, setTableOfContents] = useState<{ id: string; text: string; level: number }[]>([])
  const [activeHeading, setActiveHeading] = useState<string | null>(null)
  const [tocCollapsed, setTocCollapsed] = useState(false)
  const [selectionPopup, setSelectionPopup] = useState<{ show: boolean; x: number; y: number; text: string }>({ show: false, x: 0, y: 0, text: '' })

  // Handle text selection for inline comments
  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
      return
    }
    
    const selectedText = selection.toString().trim()
    if (selectedText.length >= 5) {
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      setSelectionPopup({
        show: true,
        x: rect.left + rect.width / 2,
        y: rect.top - 10,
        text: selectedText
      })
    } else {
      setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
    }
  }, [])

  const handleAddComment = useCallback(() => {
    if (selectionPopup.text && onTextSelect) {
      onTextSelect(selectionPopup.text)
      setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
      window.getSelection()?.removeAllRanges()
    }
  }, [selectionPopup.text, onTextSelect])

  // Calculate scroll progress
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget
    const scrollTop = container.scrollTop
    const scrollHeight = container.scrollHeight - container.clientHeight
    
    if (scrollHeight > 0) {
      const progress = Math.min(100, Math.round((scrollTop / scrollHeight) * 100))
      onScrollProgress?.(progress)
    }
    
    // Update active heading based on scroll position
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6')
    let currentActive = null
    
    headings.forEach((heading) => {
      const rect = heading.getBoundingClientRect()
      const containerRect = container.getBoundingClientRect()
      if (rect.top <= containerRect.top + 100) {
        currentActive = heading.id
      }
    })
    
    if (currentActive && currentActive !== activeHeading) {
      setActiveHeading(currentActive)
    }
  }

  // Find previewable attachments (PDF, images, or Word docs)
  const previewableAttachments = attachments.filter(
    (a) => a.mime_type === 'application/pdf' || 
           a.mime_type.startsWith('image/') ||
           a.mime_type === 'application/msword' ||
           a.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  )

  const isWordDoc = (att: Attachment | null) => {
    if (!att) return false
    return att.mime_type === 'application/msword' || 
           att.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  }

  // Extract headings from HTML content and add IDs
  const processHtmlWithHeadings = (html: string) => {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6')
    const toc: { id: string; text: string; level: number }[] = []

    headings.forEach((heading, index) => {
      const text = heading.textContent?.trim() || `Heading ${index + 1}`
      const id = `heading-${index}-${text.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
      heading.setAttribute('id', id)
      heading.classList.add('scroll-mt-4')
      
      const level = parseInt(heading.tagName.charAt(1))
      toc.push({ id, text, level })
    })

    setTableOfContents(toc)
    return doc.body.innerHTML
  }

  useEffect(() => {
    if (previewableAttachments.length > 0 && !selectedAttachment) {
      setSelectedAttachment(previewableAttachments[0])
    }
  }, [previewableAttachments, selectedAttachment])

  useEffect(() => {
    if (!selectedAttachment) {
      setPreviewUrl(null)
      setHtmlContent(null)
      setTableOfContents([])
      return
    }

    const loadPreview = async () => {
      setIsLoading(true)
      setError(null)
      
      try {
        const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
        
        if (isWordDoc(selectedAttachment)) {
          // Convert Word doc to HTML using mammoth
          const arrayBuffer = await blob.arrayBuffer()
          const result = await mammoth.convertToHtml({ arrayBuffer })
          const processedHtml = processHtmlWithHeadings(result.value)
          setHtmlContent(processedHtml)
          setPreviewUrl(null)
        } else {
          // For PDFs and images, create object URL
          const url = URL.createObjectURL(blob)
          setPreviewUrl(url)
          setHtmlContent(null)
          setTableOfContents([])
        }
      } catch (e) {
        console.error('Preview load error:', e)
        setError('Failed to load preview')
        setPreviewUrl(null)
        setHtmlContent(null)
        setTableOfContents([])
      } finally {
        setIsLoading(false)
      }
    }

    loadPreview()

    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [selectedAttachment, documentId])

  if (attachments.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
        <div className="text-6xl mb-4">📄</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Document Attached</h3>
        <p className="text-gray-500">Upload a PDF or Word document to preview it here.</p>
      </div>
    )
  }

  if (previewableAttachments.length === 0) {
    const firstAttachment = attachments[0]
    
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
        <div className="text-6xl mb-4">📎</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Preview Not Available</h3>
        <p className="text-gray-500 mb-4">
          This document type cannot be previewed.
          <br />
          Download the file to view it.
        </p>
        {firstAttachment && (
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/documents/${documentId}/attachments/${firstAttachment.id}/download`}
            download={firstAttachment.filename}
            onClick={async (e) => {
              e.preventDefault()
              try {
                const blob = await api.getAttachmentBlob(documentId, firstAttachment.id)
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = firstAttachment.filename
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                URL.revokeObjectURL(url)
              } catch (err) {
                console.error('Download failed:', err)
              }
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download {firstAttachment.filename}
          </a>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Attachment selector if multiple */}
      {previewableAttachments.length > 1 && (
        <div className="border-b border-gray-200 p-3 bg-gray-50">
          <select
            value={selectedAttachment?.id || ''}
            onChange={(e) => {
              const att = previewableAttachments.find((a) => a.id === Number(e.target.value))
              setSelectedAttachment(att || null)
            }}
            className="px-3 py-1.5 border rounded-lg text-sm"
          >
            {previewableAttachments.map((att) => (
              <option key={att.id} value={att.id}>
                {att.filename} {isWordDoc(att) ? '(Word)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Preview area */}
      <div className="relative" style={{ minHeight: '600px' }}>
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2">⚠️</div>
              <p className="text-red-600">{error}</p>
            </div>
          </div>
        ) : isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : htmlContent ? (
          // Word document rendered as HTML (read-only) with TOC sidebar
          <div className="flex h-[70vh]">
            {/* Table of Contents Sidebar */}
            {tableOfContents.length > 0 && (
              <div className={`bg-gray-50 border-r border-gray-200 transition-all duration-300 ${tocCollapsed ? 'w-10' : 'w-64'} flex-shrink-0`}>
                <div className="sticky top-0">
                  {/* TOC Header */}
                  <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-white">
                    {!tocCollapsed && (
                      <h3 className="font-medium text-sm text-gray-700 flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                        Contents
                      </h3>
                    )}
                    <button
                      onClick={() => setTocCollapsed(!tocCollapsed)}
                      className="p-1 hover:bg-gray-200 rounded text-gray-500"
                      title={tocCollapsed ? 'Expand' : 'Collapse'}
                    >
                      <svg className={`w-4 h-4 transition-transform ${tocCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                      </svg>
                    </button>
                  </div>
                  
                  {/* TOC Items */}
                  {!tocCollapsed && (
                    <nav className="p-2 overflow-y-auto" style={{ maxHeight: 'calc(70vh - 50px)' }}>
                      <ul className="space-y-1">
                        {tableOfContents.map((item) => (
                          <li key={item.id}>
                            <button
                              onClick={() => {
                                const element = document.getElementById(item.id)
                                if (element) {
                                  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                  setActiveHeading(item.id)
                                }
                              }}
                              className={`w-full text-left px-2 py-1.5 text-sm rounded transition-colors hover:bg-blue-50 hover:text-blue-700 ${
                                activeHeading === item.id ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600'
                              }`}
                              style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                            >
                              <span className="flex items-center gap-2">
                                {item.level === 1 && <span className="text-blue-500">●</span>}
                                {item.level === 2 && <span className="text-gray-400">○</span>}
                                {item.level >= 3 && <span className="text-gray-300">-</span>}
                                <span className="truncate">{item.text}</span>
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </nav>
                  )}
                </div>
              </div>
            )}

            {/* Document Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Document header bar */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-2 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                  </svg>
                  <span className="font-medium truncate">{documentTitle || selectedAttachment?.filename}</span>
                </div>
                <div className="flex items-center gap-2">
                  {tableOfContents.length > 0 && (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded">
                      {tableOfContents.length} sections
                    </span>
                  )}
                  <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">Read Only</span>
                </div>
              </div>
              
              {/* Document content with text selection for inline comments */}
              <div className="flex-1 relative overflow-auto">
                <div 
                  id="document-content-area"
                  className="p-6 prose prose-sm max-w-none document-preview-content bg-white"
                  style={{
                    fontFamily: 'Georgia, "Times New Roman", serif',
                    lineHeight: '1.8',
                    minHeight: '100%',
                  }}
                  dangerouslySetInnerHTML={{ __html: htmlContent }}
                  onScroll={handleScroll}
                  onMouseUp={handleMouseUp}
                />
                
                {/* Text selection popup for adding inline comment */}
                {selectionPopup.show && (
                  <div
                    className="fixed z-50 transform -translate-x-1/2 -translate-y-full"
                    style={{ left: selectionPopup.x, top: selectionPopup.y }}
                  >
                    <button
                      onClick={handleAddComment}
                      className="flex items-center gap-1 px-3 py-1.5 bg-yellow-500 text-white text-xs font-medium rounded-full shadow-lg hover:bg-yellow-600 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      Comment on selection
                    </button>
                    <div className="absolute left-1/2 transform -translate-x-1/2 top-full">
                      <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-yellow-500"></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : previewUrl && selectedAttachment?.mime_type === 'application/pdf' ? (
          <iframe
            src={previewUrl}
            className="w-full h-full absolute inset-0"
            style={{ minHeight: '600px' }}
            title="Document Preview"
          />
        ) : previewUrl && selectedAttachment?.mime_type.startsWith('image/') ? (
          <div className="p-4 flex items-center justify-center">
            <img
              src={previewUrl}
              alt={selectedAttachment.filename}
              className="max-w-full max-h-[600px] object-contain"
            />
          </div>
        ) : null}
      </div>

      {/* Download button */}
      {selectedAttachment && (
        <div className="border-t border-gray-200 p-3 bg-gray-50 flex justify-between items-center">
          <span className="text-sm text-gray-600">
            {documentTitle || selectedAttachment.filename}
            {isWordDoc(selectedAttachment) && (
              <span className="ml-2 text-xs text-blue-600">(Converted from Word)</span>
            )}
          </span>
          <a
            href={api.getAttachmentDownloadUrl(documentId, selectedAttachment.id)}
            download
            onClick={async (e) => {
              e.preventDefault()
              try {
                const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                // Use document title for download filename, keeping original extension
                const extension = selectedAttachment.filename.split('.').pop() || 'docx'
                const downloadName = documentTitle ? `${documentTitle}.${extension}` : selectedAttachment.filename
                a.download = downloadName
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                URL.revokeObjectURL(url)
              } catch (err) {
                console.error('Download failed:', err)
              }
            }}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Download Original
          </a>
        </div>
      )}
    </div>
  )
}