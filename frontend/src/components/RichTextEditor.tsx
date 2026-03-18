import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import { useEffect, useState } from 'react'
import { documentSnippets } from '@/lib/documentSnippets'

interface RichTextEditorProps {
  content: string
  onChange?: (html: string) => void
  editable?: boolean
  className?: string
  scrollable?: boolean
  minHeightClass?: string
  placeholder?: string
  saveStatus?: 'saved' | 'saving' | 'unsaved'
}

const MenuBar = ({ editor }: { editor: ReturnType<typeof useEditor> }) => {
  const [selectedSnippet, setSelectedSnippet] = useState('')

  if (!editor) {
    return null
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto rounded-t-xl border-b border-slate-200 bg-slate-50 p-2" role="toolbar" aria-label="Text formatting">
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={`rounded-lg px-2 py-1 text-sm font-medium ${
          editor.isActive('bold') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Bold"
        aria-label="Bold"
        aria-pressed={editor.isActive('bold')}
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('italic') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Italic"
        aria-label="Italic"
        aria-pressed={editor.isActive('italic')}
      >
        <em>I</em>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('underline') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Underline"
        aria-label="Underline"
        aria-pressed={editor.isActive('underline')}
      >
        <u>U</u>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleStrike().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('strike') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Strikethrough"
        aria-label="Strikethrough"
        aria-pressed={editor.isActive('strike')}
      >
        <s>S</s>
      </button>

      <div className="mx-1 h-6 w-px bg-slate-300" />

      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('heading', { level: 1 }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Heading 1"
        aria-label="Heading 1"
        aria-pressed={editor.isActive('heading', { level: 1 })}
      >
        H1
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('heading', { level: 2 }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Heading 2"
        aria-label="Heading 2"
        aria-pressed={editor.isActive('heading', { level: 2 })}
      >
        H2
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('heading', { level: 3 }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Heading 3"
        aria-label="Heading 3"
        aria-pressed={editor.isActive('heading', { level: 3 })}
      >
        H3
      </button>

      <div className="mx-1 h-6 w-px bg-slate-300" />

      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('bulletList') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Bullet List"
        aria-label="Bullet list"
        aria-pressed={editor.isActive('bulletList')}
      >
        Bullets
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('orderedList') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Numbered List"
        aria-label="Numbered list"
        aria-pressed={editor.isActive('orderedList')}
      >
        Numbers
      </button>

      <div className="mx-1 h-6 w-px bg-slate-300" />

      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive({ textAlign: 'left' }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Align Left"
        aria-label="Align left"
        aria-pressed={editor.isActive({ textAlign: 'left' })}
      >
        Left
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive({ textAlign: 'center' }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Align Center"
        aria-label="Align center"
        aria-pressed={editor.isActive({ textAlign: 'center' })}
      >
        Center
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive({ textAlign: 'right' }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Align Right"
        aria-label="Align right"
        aria-pressed={editor.isActive({ textAlign: 'right' })}
      >
        Right
      </button>

      <div className="mx-1 h-6 w-px bg-slate-300" />

      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('blockquote') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Quote"
        aria-label="Block quote"
        aria-pressed={editor.isActive('blockquote')}
      >
        Quote
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        className={`rounded-lg px-2 py-1 text-sm ${
          editor.isActive('codeBlock') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Code Block"
        aria-label="Code block"
        aria-pressed={editor.isActive('codeBlock')}
      >
        Code
      </button>

      <div className="mx-1 h-6 w-px bg-slate-300" />

      <button
        type="button"
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        className="rounded-lg px-2 py-1 text-sm hover:bg-slate-200 disabled:opacity-50"
        title="Undo"
        aria-label="Undo"
      >
        Undo
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        className="rounded-lg px-2 py-1 text-sm hover:bg-slate-200 disabled:opacity-50"
        title="Redo"
        aria-label="Redo"
      >
        Redo
      </button>

      <div className="ml-auto flex items-center gap-2">
        <label htmlFor="document-snippet-select" className="text-xs font-medium text-slate-500">
          Snippets
        </label>
        <select
          id="document-snippet-select"
          value={selectedSnippet}
          onChange={(event) => {
            const nextSnippetId = event.target.value
            setSelectedSnippet(nextSnippetId)
            const selectedSnippetDefinition = documentSnippets.find(
              (snippet) => snippet.id === nextSnippetId,
            )
            if (!selectedSnippetDefinition) {
              return
            }
            editor.chain().focus().insertContent(selectedSnippetDefinition.html).run()
            setSelectedSnippet('')
          }}
          className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700"
        >
          <option value="">Insert snippet...</option>
          {documentSnippets.map((snippet) => (
            <option key={snippet.id} value={snippet.id}>
              {snippet.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

export default function RichTextEditor({
  content,
  onChange,
  editable = true,
  className = '',
  scrollable = false,
  minHeightClass = 'min-h-[400px]',
  placeholder = 'Start writing your document content...',
  saveStatus,
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Placeholder.configure({
        placeholder,
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content,
    editable,
    onUpdate: ({ editor: currentEditor }) => {
      if (onChange) {
        onChange(currentEditor.getHTML())
      }
    },
  })

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content)
    }
  }, [content, editor])

  useEffect(() => {
    if (editor) {
      editor.setEditable(editable)
    }
  }, [editable, editor])

  return (
    <div
      className={`overflow-hidden rounded-xl border border-slate-300 ${scrollable ? 'flex h-full flex-col' : ''} ${className}`}
    >
      {editable ? <MenuBar editor={editor} /> : null}
      {editable && saveStatus && (
        <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50/50 px-3 py-1 text-xs text-slate-400">
          {saveStatus === 'saving' && (
            <><span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-400" /> Saving...</>
          )}
          {saveStatus === 'saved' && (
            <><span className="inline-block h-2 w-2 rounded-full bg-emerald-400" /> All changes saved</>
          )}
          {saveStatus === 'unsaved' && (
            <><span className="inline-block h-2 w-2 rounded-full bg-slate-300" /> Unsaved changes</>
          )}
        </div>
      )}
      <EditorContent
        editor={editor}
        className={`prose max-w-none p-4 focus:outline-none ${minHeightClass} ${
          scrollable ? 'flex-1 overflow-y-auto' : ''
        } ${editable ? 'bg-white' : 'bg-slate-50'}`}
      />
    </div>
  )
}
