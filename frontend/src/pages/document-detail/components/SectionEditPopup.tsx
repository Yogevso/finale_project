import { useState } from 'react'
import { Edit3, Save, Send, X } from 'lucide-react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import type { SectionEditTarget } from '@/pages/document-detail/helpers/previewHelpers'

interface SectionEditPopupProps {
  section: SectionEditTarget
  onClose: () => void
  onSave: (newHtml: string, submitForReview: boolean) => Promise<void>
  onBack?: () => void
}

export function SectionEditPopup({ section, onClose, onSave, onBack }: SectionEditPopupProps) {
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

  const popupTitle =
    section.editMode === 'insert'
      ? 'Add New Section'
      : section.editMode === 'full'
        ? 'Edit Document Content'
        : `Edit Section: ${section.text}`

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div className="flex items-center gap-3">
            <Edit3 className="w-5 h-5 text-white" />
            <h2 className="text-lg font-display font-semibold text-white">{popupTitle}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {editor && (
          <div className="flex flex-wrap gap-1 p-2 border-b border-slate-200 bg-slate-50">
            <button
              onClick={() => editor.chain().focus().toggleBold().run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('bold') ? 'bg-slate-200' : ''
              }`}
              title="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('italic') ? 'bg-slate-200' : ''
              }`}
              title="Italic"
            >
              <em>I</em>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('underline') ? 'bg-slate-200' : ''
              }`}
              title="Underline"
            >
              <span className="underline">U</span>
            </button>
            <div className="w-px bg-slate-300 mx-1" />
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('heading', { level: 2 }) ? 'bg-slate-200' : ''
              }`}
              title="Heading 2"
            >
              H2
            </button>
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('heading', { level: 3 }) ? 'bg-slate-200' : ''
              }`}
              title="Heading 3"
            >
              H3
            </button>
            <div className="w-px bg-slate-300 mx-1" />
            <button
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('bulletList') ? 'bg-slate-200' : ''
              }`}
              title="Bullet List"
            >
              • List
            </button>
            <button
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('orderedList') ? 'bg-slate-200' : ''
              }`}
              title="Numbered List"
            >
              1. List
            </button>
          </div>
        )}

        <div className="flex-1 overflow-auto bg-white">
          <EditorContent editor={editor} className="min-h-[300px]" />
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50">
          <div className="text-sm text-slate-600">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={submitForReview}
                onChange={(event) => setSubmitForReview(event.target.checked)}
                className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
              />
              <span className="flex items-center gap-2">
                <Send className="w-4 h-4" />
                Submit for review after saving
              </span>
            </label>
            <p className="text-xs text-slate-400 mt-1 ml-6">
              An admin/manager will review and approve your changes
            </p>
          </div>
          <div className="flex gap-3">
            {onBack && (
              <button onClick={onBack} className="btn-ghost">
                Back
              </button>
            )}
            <button onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
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
