import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { Attachment } from '@/types'
import { X, Send, ChevronLeft, ChevronRight, Edit3, Save, Maximize2, Minimize2, MessageSquare, FileText, Home } from 'lucide-react'
import mammoth from 'mammoth'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'

interface TocItem {
  id: string
  text: string
  level: number
  html: string
  startIndex: number
  endIndex: number
}

interface SectionEditPopupProps {
  section: TocItem
  onClose: () => void
  onSave: (newHtml: string, submitForReview: boolean) => Promise<void>
}

// Section Edit Popup with TipTap editor
function SectionEditPopup({ section, onClose, onSave }: SectionEditPopupProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [submitForReview, setSubmitForReview] = useState(true)
  
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: section.html,
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[200px] p-4',
      },
    },
  })

  const handleSave = async () => {
    if (!editor) return
    setIsSaving(true)
    try {
      await onSave(editor.getHTML(), submitForReview)
      onClose()
    } catch (error) {
      console.error('Failed to save section:', error)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div className="flex items-center gap-3">
            <Edit3 className="w-5 h-5 text-white" />
            <h2 className="text-lg font-display font-semibold text-white">Edit Section: {section.text}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toolbar */}
        {editor && (
          <div className="flex flex-wrap gap-1 p-2 border-b border-slate-200 bg-slate-50">
            <button
              onClick={() => editor.chain().focus().toggleBold().run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('bold') ? 'bg-slate-200' : ''}`}
              title="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('italic') ? 'bg-slate-200' : ''}`}
              title="Italic"
            >
              <em>I</em>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('underline') ? 'bg-slate-200' : ''}`}
              title="Underline"
            >
              <span className="underline">U</span>
            </button>
            <div className="w-px bg-slate-300 mx-1" />
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('heading', { level: 2 }) ? 'bg-slate-200' : ''}`}
              title="Heading 2"
            >
              H2
            </button>
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('heading', { level: 3 }) ? 'bg-slate-200' : ''}`}
              title="Heading 3"
            >
              H3
            </button>
            <div className="w-px bg-slate-300 mx-1" />
            <button
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('bulletList') ? 'bg-slate-200' : ''}`}
              title="Bullet List"
            >
              • List
            </button>
            <button
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={`p-2 rounded hover:bg-slate-200 ${editor.isActive('orderedList') ? 'bg-slate-200' : ''}`}
              title="Numbered List"
            >
              1. List
            </button>
          </div>
        )}

        {/* Editor Content */}
        <div className="flex-1 overflow-auto bg-white">
          <EditorContent editor={editor} className="min-h-[300px]" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={submitForReview}
                onChange={(e) => setSubmitForReview(e.target.checked)}
                className="w-4 h-4 text-sky-600 rounded focus:ring-sky-500"
              />
              <span className="text-sm text-slate-600">Submit for review after saving</span>
            </label>
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className={`btn-primary flex items-center gap-2 disabled:opacity-50 ${
                submitForReview 
                  ? '' 
                  : '!bg-amber-500 hover:!bg-amber-600'
              }`}
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : submitForReview ? 'Save & Submit for Review' : 'Save as Draft'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DocumentFullscreenPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user, isEditor } = useAuth()
  const queryClient = useQueryClient()
  const contentRef = useRef<HTMLDivElement>(null)
  
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [tableOfContents, setTableOfContents] = useState<TocItem[]>([])
  const [activeHeading, setActiveHeading] = useState<string | null>(null)
  const [tocCollapsed, setTocCollapsed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [editingSection, setEditingSection] = useState<TocItem | null>(null)
  
  // Comment popup state
  const [commentPopup, setCommentPopup] = useState<{ show: boolean; x: number; y: number; text: string; anchorId: string }>({ show: false, x: 0, y: 0, text: '', anchorId: '' })
  const [commentText, setCommentText] = useState('')
  const [isPrivateComment, setIsPrivateComment] = useState(false)
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)
  const [selectionPopup, setSelectionPopup] = useState<{ show: boolean; x: number; y: number; text: string }>({ show: false, x: 0, y: 0, text: '' })

  const { data: documentData } = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.getDocument(Number(id)),
    enabled: !!id,
  })

  const { data: attachmentsData } = useQuery({
    queryKey: ['attachments', id],
    queryFn: () => api.getAttachments(Number(id)),
    enabled: !!id,
  })
  const attachments = useMemo(() => attachmentsData ?? [], [attachmentsData])

  // Comment mutation
  const createCommentMutation = useMutation({
    mutationFn: (data: { content: string; is_private?: boolean; anchor_text?: string; anchor_id?: string }) => 
      api.createComment(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', id] })
      setCommentPopup({ show: false, x: 0, y: 0, text: '', anchorId: '' })
      setCommentText('')
      setIsPrivateComment(false)
      setIsSubmittingComment(false)
    },
  })

  // Extract sections from HTML content
  const processHtmlWithSections = useCallback((html: string): TocItem[] => {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const elements = Array.from(doc.body.children)
    const toc: TocItem[] = []
    
    let currentSection: { heading: Element | null; content: Element[]; startIndex: number } = { heading: null, content: [], startIndex: 0 }
    
    elements.forEach((el, index) => {
      const tagName = el.tagName.toLowerCase()
      if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
        // Save previous section
        if (currentSection.heading || currentSection.content.length > 0) {
          const headingText = currentSection.heading?.textContent?.trim() || 'Untitled Section'
          const sectionId = `section-${toc.length}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
          
          // Build section HTML
          const sectionHtml = [
            currentSection.heading?.outerHTML || '',
            ...currentSection.content.map(c => c.outerHTML)
          ].join('\n')
          
          toc.push({
            id: sectionId,
            text: headingText,
            level: currentSection.heading ? parseInt(currentSection.heading.tagName.charAt(1)) : 1,
            html: sectionHtml,
            startIndex: currentSection.startIndex,
            endIndex: index - 1
          })
        }
        
        // Start new section
        currentSection = { heading: el, content: [], startIndex: index }
        el.setAttribute('id', `heading-${toc.length}`)
      } else {
        currentSection.content.push(el)
      }
    })
    
    // Save last section
    if (currentSection.heading || currentSection.content.length > 0) {
      const headingText = currentSection.heading?.textContent?.trim() || 'Content'
      const sectionId = `section-${toc.length}-${headingText.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)}`
      
      const sectionHtml = [
        currentSection.heading?.outerHTML || '',
        ...currentSection.content.map(c => c.outerHTML)
      ].join('\n')
      
      toc.push({
        id: sectionId,
        text: headingText,
        level: currentSection.heading ? parseInt(currentSection.heading.tagName.charAt(1)) : 1,
        html: sectionHtml,
        startIndex: currentSection.startIndex,
        endIndex: elements.length - 1
      })
    }
    
    return toc
  }, [])

  const isSyntheticUploadPlaceholder = useCallback((content?: string | null) => {
    if (!content) return false
    return content.trim().toLowerCase().startsWith('uploaded from file:')
  }, [])

  // Load document content
  useEffect(() => {
    const loadContent = async () => {
      try {
        // First, check if there's a version with content (published preferred)
        const versionsResponse = await api.getVersions(Number(id))
        const withContent = versionsResponse.items
          .filter((v) => !!v.content?.trim() && !isSyntheticUploadPlaceholder(v.content))
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        const publishedVersion = withContent
          .filter(v => v.is_published)
          .sort((a, b) => new Date(b.published_at || b.created_at).getTime() - new Date(a.published_at || a.created_at).getTime())[0]
        let versionToShow = publishedVersion || withContent[0]

        if (!versionToShow && versionsResponse.items.length > 0) {
          const fullVersion = await api.getVersion(Number(id), versionsResponse.items[0].id)
          if (fullVersion?.content) {
            versionToShow = fullVersion
          }
        }

        if (versionToShow?.content) {
          const sections = processHtmlWithSections(versionToShow.content)
          setTableOfContents(sections)

          const parser = new DOMParser()
          const doc = parser.parseFromString(versionToShow.content, 'text/html')
          const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6')
          headings.forEach((heading, index) => {
            heading.setAttribute('id', `heading-${index}`)
            heading.classList.add('scroll-mt-4')
          })
          setHtmlContent(doc.body.innerHTML)
          setIsLoading(false)
          return
        }

        // Fall back to converting Word attachment if available
        const wordAttachment = attachments.find(
          (a: Attachment) => a.mime_type === 'application/msword' || 
               a.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        if (wordAttachment) {
          const blob = await api.getAttachmentOriginalBlob(Number(id), wordAttachment.id)
          const arrayBuffer = await blob.arrayBuffer()
          const result = await mammoth.convertToHtml({ arrayBuffer })
          
          const sections = processHtmlWithSections(result.value)
          setTableOfContents(sections)
          
          const parser = new DOMParser()
          const doc = parser.parseFromString(result.value, 'text/html')
          const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6')
          headings.forEach((heading, index) => {
            heading.setAttribute('id', `heading-${index}`)
            heading.classList.add('scroll-mt-4')
          })
          setHtmlContent(doc.body.innerHTML)
        } else if (attachments.length) {
          setHtmlContent('<div class="text-center p-8"><p class="text-slate-500">Document content is being processed. Please refresh the page.</p></div>')
        } else {
          setHtmlContent('<div class="text-center p-8"><p class="text-slate-500">No content yet.</p></div>')
        }
      } catch (e) {
        console.error('Failed to load document:', e)
        setError('Failed to load document content')
      } finally {
        setIsLoading(false)
      }
    }

    loadContent()
  }, [attachments, id, isSyntheticUploadPlaceholder, processHtmlWithSections])

  // Handle section save
  const handleSaveSection = async (sectionIndex: number, newHtml: string, submitForReview: boolean) => {
    if (!htmlContent || !editingSection) return
    
    // Get old section content for comparison
    const oldSectionHtml = editingSection.html
    
    // Replace section in full HTML
    const updatedToc = [...tableOfContents]
    updatedToc[sectionIndex] = { ...updatedToc[sectionIndex], html: newHtml }
    
    // Rebuild full HTML from sections
    const newFullHtml = updatedToc.map(s => s.html).join('\n')
    setHtmlContent(newFullHtml)
    setTableOfContents(processHtmlWithSections(newFullHtml))
    
    // Create detailed change summary
    const changesSummary = `Section edited: "${editingSection.text}"\n\n` +
      `--- Original content ---\n${oldSectionHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${oldSectionHtml.length > 500 ? '...' : ''}\n\n` +
      `--- New content ---\n${newHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${newHtml.length > 500 ? '...' : ''}`
    
    // Save as new version (draft)
    const version = await api.createVersion(Number(id), {
      content: newFullHtml,
      changes_summary: changesSummary,
    })
    
    // Set document status back to draft so it requires approval
    await api.updateDocument(Number(id), { status: 'draft' })
    
    // If submitForReview is checked, auto-submit for review
    if (submitForReview) {
      await api.submitForReview(Number(id), {
        version_id: version.id,
        message: `Edited section: "${editingSection.text}"`,
      })
    }
    
    queryClient.invalidateQueries({ queryKey: ['versions', id] })
    queryClient.invalidateQueries({ queryKey: ['document', id] })
    queryClient.invalidateQueries({ queryKey: ['reviews'] })
  }

  // Text selection for comments
  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.inline-comment-popup')) return
    
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      if (!commentPopup.show) {
        setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
      }
      return
    }
    
    const selectedText = selection.toString().trim()
    if (selectedText.length >= 3) {
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      setSelectionPopup({
        show: true,
        x: rect.left + rect.width / 2,
        y: rect.top - 10,
        text: selectedText
      })
    }
  }, [commentPopup.show])

  const handleOpenCommentForm = useCallback(() => {
    if (selectionPopup.text) {
      const anchorId = `anchor-${Date.now()}`
      setCommentPopup({
        show: true,
        x: selectionPopup.x,
        y: selectionPopup.y + 60,
        text: selectionPopup.text,
        anchorId
      })
      setSelectionPopup({ show: false, x: 0, y: 0, text: '' })
    }
  }, [selectionPopup])

  const handleSubmitComment = useCallback(() => {
    if (!commentText.trim()) return
    setIsSubmittingComment(true)
    createCommentMutation.mutate({
      content: commentText.trim(),
      is_private: isPrivateComment,
      anchor_text: commentPopup.text,
      anchor_id: commentPopup.anchorId
    })
  }, [commentText, isPrivateComment, commentPopup, createCommentMutation])

  const handleCloseCommentPopup = useCallback(() => {
    setCommentPopup({ show: false, x: 0, y: 0, text: '', anchorId: '' })
    setCommentText('')
    setIsPrivateComment(false)
    window.getSelection()?.removeAllRanges()
  }, [])

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!window.document.fullscreenElement) {
      window.document.documentElement.requestFullscreen()
      setIsFullscreen(true)
    } else {
      window.document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  // Handle scroll for active heading
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget
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

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-white flex items-center justify-center z-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading document...</p>
        </div>
      </div>
    )
  }

  if (error || !documentData) {
    return (
      <div className="fixed inset-0 bg-white flex items-center justify-center z-50">
        <div className="text-center">
          <div className="text-6xl mb-4">📄</div>
          <h2 className="text-xl font-display font-semibold text-slate-900 mb-2">Document Not Found</h2>
          <p className="text-slate-600 mb-4">{error || 'Unable to load document'}</p>
          <button
            onClick={() => navigate('/documents')}
            className="btn-primary"
          >
            Back to Documents
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-white flex flex-col z-40">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-sky-600 to-sky-700 text-white shadow-lg flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/documents/${id}`)}
            className="flex items-center gap-2 px-3 py-1.5 bg-white/20 rounded-lg hover:bg-white/30 transition-colors"
          >
            <Home className="w-4 h-4" />
            <span className="text-sm">Exit Fullscreen</span>
          </button>
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            <h1 className="text-lg font-display font-semibold truncate max-w-md">{documentData.title}</h1>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <span className="text-xs bg-white/20 px-2 py-1 rounded">
            {tableOfContents.length} sections
          </span>
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Table of Contents Sidebar */}
        <div className={`bg-slate-50 border-r border-slate-200 transition-all duration-300 ${tocCollapsed ? 'w-12' : 'w-72'} flex-shrink-0 flex flex-col`}>
          {/* TOC Header */}
          <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-white flex-shrink-0">
            {!tocCollapsed && (
              <h3 className="font-medium text-sm text-slate-700 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                Contents
              </h3>
            )}
            <button
              onClick={() => setTocCollapsed(!tocCollapsed)}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-500"
              title={tocCollapsed ? 'Expand' : 'Collapse'}
            >
              {tocCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>
          
          {/* TOC Items */}
          {!tocCollapsed && (
            <nav className="flex-1 p-2 overflow-y-auto">
              <ul className="space-y-1">
                {tableOfContents.map((item, index) => (
                  <li key={item.id} className="group">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => {
                          const element = window.document.getElementById(`heading-${index}`)
                          if (element) {
                            element.scrollIntoView({ behavior: 'smooth', block: 'start' })
                            setActiveHeading(`heading-${index}`)
                          }
                        }}
                        className={`flex-1 text-left px-2 py-2 text-sm rounded-l transition-colors hover:bg-sky-50 hover:text-sky-700 ${
                          activeHeading === `heading-${index}` ? 'bg-sky-100 text-sky-700 font-medium' : 'text-slate-600'
                        }`}
                        style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                      >
                        <span className="flex items-center gap-2">
                          {item.level === 1 && <span className="text-sky-500">●</span>}
                          {item.level === 2 && <span className="text-slate-400">○</span>}
                          {item.level >= 3 && <span className="text-slate-300">-</span>}
                          <span className="truncate">{item.text}</span>
                        </span>
                      </button>
                      {isEditor && (
                        <button
                          onClick={() => setEditingSection(item)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-sky-100 rounded text-sky-600 transition-opacity"
                          title="Edit section"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </nav>
          )}
        </div>

        {/* Document Content */}
        <div 
          ref={contentRef}
          className="flex-1 overflow-auto document-preview-pane"
          onScroll={handleScroll}
          onMouseUp={handleMouseUp}
        >
          <div className="document-preview-paper">
            <div
              className="document-preview-content"
              dangerouslySetInnerHTML={{ __html: htmlContent || '' }}
            />
          </div>
          
          {/* Text selection popup for comments */}
          {selectionPopup.show && !commentPopup.show && (
            <div
              className="fixed z-50 transform -translate-x-1/2 -translate-y-full"
              style={{ left: selectionPopup.x, top: selectionPopup.y }}
            >
              <button
                onClick={handleOpenCommentForm}
                className="flex items-center gap-1 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full shadow-lg hover:bg-amber-600 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Add Comment
              </button>
              <div className="absolute left-1/2 transform -translate-x-1/2 top-full">
                <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-amber-500"></div>
              </div>
            </div>
          )}
          
          {/* Comment form popup */}
          {commentPopup.show && user && (
            <div
              className="inline-comment-popup fixed z-50 transform -translate-x-1/2"
              style={{ left: Math.max(180, Math.min(commentPopup.x, window.innerWidth - 180)), top: commentPopup.y }}
            >
              <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-80 overflow-hidden">
                <div className="bg-amber-50 border-b border-amber-100 px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-amber-800 mb-1">Commenting on:</p>
                      <p className="text-sm text-amber-700 italic line-clamp-2">"{commentPopup.text.slice(0, 100)}{commentPopup.text.length > 100 ? '...' : ''}"</p>
                    </div>
                    <button onClick={handleCloseCommentPopup} className="p-1 hover:bg-amber-100 rounded text-amber-600">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <div className="p-4 space-y-3">
                  <textarea
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder="Write your comment..."
                    className="input-field resize-none"
                    rows={3}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmitComment()
                      if (e.key === 'Escape') handleCloseCommentPopup()
                    }}
                  />
                  
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isPrivateComment}
                        onChange={(e) => setIsPrivateComment(e.target.checked)}
                        className="rounded border-slate-300 text-amber-500 focus:ring-amber-500"
                      />
                      <span>🔒 Private</span>
                    </label>
                    
                    <div className="flex gap-2">
                      <button onClick={handleCloseCommentPopup} className="btn-ghost text-sm">
                        Cancel
                      </button>
                      <button
                        onClick={handleSubmitComment}
                        disabled={!commentText.trim() || isSubmittingComment}
                        className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 flex items-center gap-1"
                      >
                        {isSubmittingComment ? 'Posting...' : <><Send className="w-3.5 h-3.5" /> Post</>}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Section Edit Popup */}
      {editingSection && (
        <SectionEditPopup
          section={editingSection}
          onClose={() => setEditingSection(null)}
          onSave={async (newHtml, submitForReview) => {
            const index = tableOfContents.findIndex(s => s.id === editingSection.id)
            if (index !== -1) {
              await handleSaveSection(index, newHtml, submitForReview)
            }
          }}
        />
      )}
    </div>
  )
}
