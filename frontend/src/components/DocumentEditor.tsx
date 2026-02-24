import { useEffect, useMemo, useState } from 'react'
import mammoth from 'mammoth'
import RichTextEditor from './RichTextEditor'
import CollaborativeEditor from './CollaborativeEditor'
import { api } from '@/lib/api'
import {
  getPreferredEditorAttachment,
  resolveSelectedAttachment,
} from '@/lib/attachmentSelection'
import { useCollaboration } from '@/lib/useCollaboration'
import { getUserColor } from '@/lib/userColors'
import { useAuth } from '@/lib/auth'
import type { Attachment } from '@/types'

interface DocumentEditorProps {
  documentId: number
  attachments: Attachment[]
  onSave?: (content: string) => Promise<void>
  isEditor: boolean
  collaborationEnabled?: boolean
}

export default function DocumentEditor({
  documentId,
  attachments,
  onSave,
  isEditor,
  collaborationEnabled = false,
}: DocumentEditorProps) {
  const { user } = useAuth()
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [originalContent, setOriginalContent] = useState<string>('')
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)

  // Collaboration hook
  const collaboration = useCollaboration({
    documentId,
    username: user?.username || 'Anonymous',
    userId: user?.id || 0,
    enabled: collaborationEnabled && isEditing && isEditor,
    onError: (err) => console.error('Collaboration error:', err),
  })

  // Get user color for collaboration
  const userColor = getUserColor(user?.id || 0)

  // Find Word documents
  const wordDocs = useMemo(
    () =>
      attachments.filter(
        (a) =>
          a.mime_type === 'application/msword' ||
          a.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      ),
    [attachments],
  )

  useEffect(() => {
    const nextSelection = resolveSelectedAttachment(
      attachments,
      selectedAttachment,
      getPreferredEditorAttachment,
    )
    if (nextSelection !== selectedAttachment) {
      setSelectedAttachment(nextSelection)
    }
  }, [attachments, selectedAttachment])

  useEffect(() => {
    const loadDocument = async () => {
      const activeSelection = resolveSelectedAttachment(
        attachments,
        selectedAttachment,
        getPreferredEditorAttachment,
      )

      if (activeSelection !== selectedAttachment) {
        setSelectedAttachment(activeSelection)
        return
      }

      if (!activeSelection) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const blob = await api.getAttachmentOriginalBlob(documentId, activeSelection.id)
        
        if (
          activeSelection.mime_type === 'application/msword' ||
          activeSelection.mime_type ===
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ) {
          // Convert Word to HTML using mammoth
          const arrayBuffer = await blob.arrayBuffer()
          const result = await mammoth.convertToHtml({ arrayBuffer })
          setContent(result.value)
          setOriginalContent(result.value)
          
          if (result.messages.length > 0) {
            console.warn('Mammoth conversion messages:', result.messages)
          }
        } else if (activeSelection.mime_type === 'application/pdf') {
          // PDFs can't be edited - show message
          setContent('<p><em>PDF documents cannot be edited. Use the Preview tab to view.</em></p>')
          setOriginalContent('')
        }
      } catch (e) {
        console.error('Failed to load document:', e)
        setError('Failed to load document content')
      } finally {
        setLoading(false)
      }
    }

    loadDocument()
  }, [attachments, documentId, selectedAttachment])

  const handleContentChange = (newContent: string) => {
    setContent(newContent)
    setHasChanges(newContent !== originalContent)
  }

  const handleSave = async () => {
    if (!onSave || !hasChanges) return

    setSaving(true)
    try {
      await onSave(content)
      setOriginalContent(content)
      setHasChanges(false)
      setIsEditing(false)
    } catch (e) {
      console.error('Failed to save:', e)
      setError('Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setContent(originalContent)
    setHasChanges(false)
    setIsEditing(false)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mx-auto mb-4"></div>
        <p className="text-slate-500">Loading document...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
        <div className="text-4xl mb-4">⚠️</div>
        <h3 className="text-lg font-medium text-rose-600 mb-2">{error}</h3>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-sky-600 text-white rounded-xl hover:bg-sky-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (attachments.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
        <div className="text-6xl mb-4">📄</div>
        <h3 className="text-lg font-medium text-slate-900 mb-2">No Document Attached</h3>
        <p className="text-slate-500">Upload a Word document to edit it here.</p>
      </div>
    )
  }

  if (wordDocs.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
        <div className="text-6xl mb-4">📎</div>
        <h3 className="text-lg font-medium text-slate-900 mb-2">Editing Not Available</h3>
        <p className="text-slate-500">
          Only Word documents (.doc, .docx) can be edited.
          <br />
          PDF files are read-only.
        </p>
      </div>
    )
  }

  const isPdf = selectedAttachment?.mime_type === 'application/pdf'

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-3">
          {wordDocs.length > 1 && (
            <select
              value={selectedAttachment?.id || ''}
              onChange={(e) => {
                const att = wordDocs.find((a) => a.id === Number(e.target.value))
                setSelectedAttachment(att || null)
              }}
              className="px-3 py-1.5 border rounded-lg text-sm"
            >
              {wordDocs.map((att) => (
                <option key={att.id} value={att.id}>
                  {att.original_filename}
                </option>
              ))}
            </select>
          )}
          {wordDocs.length === 1 && (
            <span className="text-sm text-slate-600">
              📄 {selectedAttachment?.original_filename}
            </span>
          )}
        </div>

        {isEditor && !isPdf && (
          <div className="flex items-center gap-2">
            {isEditing ? (
              <>
                <button
                  onClick={handleCancel}
                  className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !hasChanges}
                  className="px-4 py-1.5 bg-sky-600 text-white text-sm rounded-xl hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {saving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Saving...
                    </>
                  ) : (
                    <>Save Changes</>
                  )}
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-1.5 bg-sky-600 text-white text-sm rounded-xl hover:bg-sky-700 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Document
              </button>
            )}
          </div>
        )}
      </div>

      {/* Editor */}
      <div className="p-4">
        {hasChanges && !collaborationEnabled && (
          <div className="mb-3 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            You have unsaved changes
          </div>
        )}

        {/* Use CollaborativeEditor when collaboration is enabled and editing */}
        {collaborationEnabled && isEditing && user ? (
          <CollaborativeEditor
            ydoc={collaboration.ydoc}
            provider={collaboration.provider}
            isConnected={collaboration.isConnected}
            isConnecting={collaboration.isConnecting}
            isSynced={collaboration.isSynced}
            error={collaboration.error}
            collaborators={collaboration.collaborators}
            currentUser={{
              userId: user.id,
              username: user.username,
              color: userColor.color,
            }}
            content={content}
            onChange={handleContentChange}
            editable={isEditing && !isPdf}
            className={isEditing ? 'ring-2 ring-sky-500' : ''}
            onRetry={collaboration.connect}
          />
        ) : (
          <RichTextEditor
            content={content}
            onChange={handleContentChange}
            editable={isEditing && !isPdf}
            className={isEditing ? 'ring-2 ring-sky-500' : ''}
          />
        )}
      </div>
    </div>
  )
}
