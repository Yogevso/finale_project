import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
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
}

const MenuBar = ({ editor }: { editor: ReturnType<typeof useEditor> }) => {
  const [selectedSnippet, setSelectedSnippet] = useState('')

  if (!editor) {
    return null
  }

  return (
    <div className="flex flex-wrap items-center gap-1 rounded-t-xl border-b border-slate-200 bg-slate-50 p-2">
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={`rounded-lg px-2 py-1 text-sm font-medium ${
          editor.isActive('bold') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Bold"
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
      >
        Undo
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        className="rounded-lg px-2 py-1 text-sm hover:bg-slate-200 disabled:opacity-50"
        title="Redo"
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
}: RichTextEditorProps) {
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
      <EditorContent
        editor={editor}
        className={`prose max-w-none p-4 focus:outline-none ${minHeightClass} ${
          scrollable ? 'flex-1 overflow-y-auto' : ''
        } ${editable ? 'bg-white' : 'bg-slate-50'}`}
      />
    </div>
  )
}
