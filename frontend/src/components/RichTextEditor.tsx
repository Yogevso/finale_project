import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { useEffect } from 'react'

interface RichTextEditorProps {
  content: string
  onChange?: (html: string) => void
  editable?: boolean
  className?: string
}

const MenuBar = ({ editor }: { editor: ReturnType<typeof useEditor> }) => {
  if (!editor) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-1 p-2 border-b border-gray-200 bg-gray-50">
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={`px-2 py-1 rounded text-sm font-medium ${
          editor.isActive('bold') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Bold"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('italic') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Italic"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('underline') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Underline"
      >
        <u>U</u>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleStrike().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('strike') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Strikethrough"
      >
        <s>S</s>
      </button>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('heading', { level: 1 }) ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Heading 1"
      >
        H1
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('heading', { level: 2 }) ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Heading 2"
      >
        H2
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('heading', { level: 3 }) ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Heading 3"
      >
        H3
      </button>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('bulletList') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Bullet List"
      >
        • List
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('orderedList') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Numbered List"
      >
        1. List
      </button>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive({ textAlign: 'left' }) ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Align Left"
      >
        ⬅
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive({ textAlign: 'center' }) ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Align Center"
      >
        ⬌
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive({ textAlign: 'right' }) ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Align Right"
      >
        ➡
      </button>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('blockquote') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Quote"
      >
        ""
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        className={`px-2 py-1 rounded text-sm ${
          editor.isActive('codeBlock') ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
        }`}
        title="Code Block"
      >
        {'</>'}
      </button>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <button
        type="button"
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        className="px-2 py-1 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
        title="Undo"
      >
        ↩
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        className="px-2 py-1 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
        title="Redo"
      >
        ↪
      </button>
    </div>
  )
}

export default function RichTextEditor({ content, onChange, editable = true, className = '' }: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      if (onChange) {
        onChange(editor.getHTML())
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
    <div className={`border border-gray-300 rounded-lg overflow-hidden ${className}`}>
      {editable && <MenuBar editor={editor} />}
      <EditorContent 
        editor={editor} 
        className={`prose max-w-none p-4 min-h-[400px] focus:outline-none ${
          editable ? 'bg-white' : 'bg-gray-50'
        }`}
      />
    </div>
  )
}
