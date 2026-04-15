import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import Highlight from '@tiptap/extension-highlight'
import Subscript from '@tiptap/extension-subscript'
import Superscript from '@tiptap/extension-superscript'
import Link from '@tiptap/extension-link'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import { useEffect, useState, useCallback } from 'react'
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

const BLOCK_FORMATS = [
  { id: 'paragraph', label: 'Normal Text', shortLabel: 'Normal', action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().setParagraph().run() },
  { id: 'h1', label: 'Title', shortLabel: 'H1 — Title', level: 1, action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().toggleHeading({ level: 1 }).run() },
  { id: 'h2', label: 'Section Title', shortLabel: 'H2 — Section Title', level: 2, action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().toggleHeading({ level: 2 }).run() },
  { id: 'h3', label: 'Sub-section Title', shortLabel: 'H3 — Sub-section', level: 3, action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().toggleHeading({ level: 3 }).run() },
] as const

function getActiveBlockFormat(editor: NonNullable<ReturnType<typeof useEditor>>) {
  if (editor.isActive('heading', { level: 1 })) return BLOCK_FORMATS[1]
  if (editor.isActive('heading', { level: 2 })) return BLOCK_FORMATS[2]
  if (editor.isActive('heading', { level: 3 })) return BLOCK_FORMATS[3]
  return BLOCK_FORMATS[0]
}

const MenuBar = ({ editor }: { editor: ReturnType<typeof useEditor> }) => {
  const [selectedSnippet, setSelectedSnippet] = useState('')
  const [blockDropdownOpen, setBlockDropdownOpen] = useState(false)
  const [tableMenuOpen, setTableMenuOpen] = useState(false)

  const setLink = useCallback(() => {
    if (!editor) return
    const previousUrl = editor.getAttributes('link').href
    const url = window.prompt('Enter URL:', previousUrl || 'https://')
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }, [editor])

  if (!editor) {
    return null
  }

  const activeBlock = getActiveBlockFormat(editor)
  const isHeadingActive = activeBlock.id !== 'paragraph'
  const isInsideTable = editor.isActive('table')

  const tbtn = (active: boolean) =>
    `rounded-lg px-2 py-1.5 text-sm transition-colors ${
      active ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
    }`

  return (
    <div className="flex flex-col rounded-t-xl border-b border-slate-200 bg-slate-50">
      {/* Row 1: Block format + Inline + Lists + Alignment */}
      <div className="flex flex-wrap items-center gap-1 px-2 pt-2 pb-1" role="toolbar" aria-label="Text formatting">
        {/* Block format dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setBlockDropdownOpen(!blockDropdownOpen)}
            onBlur={() => setTimeout(() => setBlockDropdownOpen(false), 150)}
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-sm font-medium transition-colors ${
              isHeadingActive
                ? 'border-sky-300 bg-sky-50 text-sky-700'
                : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'
            }`}
            aria-expanded={blockDropdownOpen}
            aria-haspopup="listbox"
            aria-label={`Current format: ${activeBlock.label}`}
            title="Block format"
          >
            <span className="min-w-[7rem] text-left">{activeBlock.shortLabel ?? activeBlock.label}</span>
            <svg className={`h-3.5 w-3.5 transition-transform ${blockDropdownOpen ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" /></svg>
          </button>

          {blockDropdownOpen && (
            <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-xl border border-slate-200 bg-white py-1 shadow-lg" role="listbox">
              {BLOCK_FORMATS.map((format) => {
                const isActive = activeBlock.id === format.id
                return (
                  <button
                    key={format.id}
                    type="button"
                    role="option"
                    aria-selected={isActive}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      format.action(editor)
                      setBlockDropdownOpen(false)
                    }}
                    className={`flex w-full items-center gap-2 px-3 py-2 text-left transition-colors ${
                      isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <span className={`font-medium ${
                      format.id === 'h1' ? 'text-lg' : format.id === 'h2' ? 'text-base' : format.id === 'h3' ? 'text-sm' : 'text-sm'
                    }`}>
                      {format.label}
                    </span>
                    {format.id !== 'paragraph' && (
                      <span className="ml-auto rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        {format.id.toUpperCase()}
                      </span>
                    )}
                    {isActive && (
                      <svg className="ml-auto h-4 w-4 text-sky-600" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" /></svg>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="mx-1 h-6 w-px bg-slate-300" />

        {/* Inline formatting */}
        <button type="button" onClick={() => editor.chain().focus().toggleBold().run()} className={tbtn(editor.isActive('bold'))} title="Bold (Ctrl+B)" aria-label="Bold" aria-pressed={editor.isActive('bold')}><strong>B</strong></button>
        <button type="button" onClick={() => editor.chain().focus().toggleItalic().run()} className={tbtn(editor.isActive('italic'))} title="Italic (Ctrl+I)" aria-label="Italic" aria-pressed={editor.isActive('italic')}><em>I</em></button>
        <button type="button" onClick={() => editor.chain().focus().toggleUnderline().run()} className={tbtn(editor.isActive('underline'))} title="Underline (Ctrl+U)" aria-label="Underline" aria-pressed={editor.isActive('underline')}><u>U</u></button>
        <button type="button" onClick={() => editor.chain().focus().toggleStrike().run()} className={tbtn(editor.isActive('strike'))} title="Strikethrough" aria-label="Strikethrough" aria-pressed={editor.isActive('strike')}><s>S</s></button>
        <button type="button" onClick={() => editor.chain().focus().toggleSuperscript().run()} className={tbtn(editor.isActive('superscript'))} title="Superscript" aria-label="Superscript" aria-pressed={editor.isActive('superscript')}>X<sup className="text-[9px]">2</sup></button>
        <button type="button" onClick={() => editor.chain().focus().toggleSubscript().run()} className={tbtn(editor.isActive('subscript'))} title="Subscript" aria-label="Subscript" aria-pressed={editor.isActive('subscript')}>X<sub className="text-[9px]">2</sub></button>
        <button type="button" onClick={() => editor.chain().focus().toggleHighlight().run()} className={tbtn(editor.isActive('highlight'))} title="Highlight" aria-label="Highlight" aria-pressed={editor.isActive('highlight')}>
          <span className="rounded bg-yellow-200 px-0.5">H</span>
        </button>

        <div className="mx-1 h-6 w-px bg-slate-300" />

        {/* Link */}
        <button type="button" onClick={setLink} className={tbtn(editor.isActive('link'))} title="Insert Link" aria-label="Insert link" aria-pressed={editor.isActive('link')}>Link</button>
        {editor.isActive('link') && (
          <button type="button" onClick={() => editor.chain().focus().unsetLink().run()} className="rounded-lg px-2 py-1.5 text-sm text-red-500 hover:bg-red-50 transition-colors" title="Remove Link" aria-label="Remove link">Unlink</button>
        )}

        <div className="mx-1 h-6 w-px bg-slate-300" />

        {/* Lists */}
        <button type="button" onClick={() => editor.chain().focus().toggleBulletList().run()} className={tbtn(editor.isActive('bulletList'))} title="Bullet List" aria-label="Bullet list" aria-pressed={editor.isActive('bulletList')}>Bullets</button>
        <button type="button" onClick={() => editor.chain().focus().toggleOrderedList().run()} className={tbtn(editor.isActive('orderedList'))} title="Numbered List" aria-label="Numbered list" aria-pressed={editor.isActive('orderedList')}>Numbers</button>

        <div className="mx-1 h-6 w-px bg-slate-300" />

        {/* Alignment */}
        <button type="button" onClick={() => editor.chain().focus().setTextAlign('left').run()} className={tbtn(editor.isActive({ textAlign: 'left' }))} title="Align Left" aria-label="Align left">Left</button>
        <button type="button" onClick={() => editor.chain().focus().setTextAlign('center').run()} className={tbtn(editor.isActive({ textAlign: 'center' }))} title="Align Center" aria-label="Align center">Center</button>
        <button type="button" onClick={() => editor.chain().focus().setTextAlign('right').run()} className={tbtn(editor.isActive({ textAlign: 'right' }))} title="Align Right" aria-label="Align right">Right</button>
      </div>

      {/* Row 2: Blocks + Table + Undo/Redo + Snippets */}
      <div className="flex flex-wrap items-center gap-1 px-2 pb-2 pt-1" role="toolbar" aria-label="Block and table controls">
        {/* Block elements */}
        <button type="button" onClick={() => editor.chain().focus().toggleBlockquote().run()} className={tbtn(editor.isActive('blockquote'))} title="Block Quote" aria-label="Block quote" aria-pressed={editor.isActive('blockquote')}>Quote</button>
        <button type="button" onClick={() => editor.chain().focus().toggleCodeBlock().run()} className={tbtn(editor.isActive('codeBlock'))} title="Code Block" aria-label="Code block" aria-pressed={editor.isActive('codeBlock')}>Code</button>
        <button type="button" onClick={() => editor.chain().focus().setHorizontalRule().run()} className="rounded-lg px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-200 transition-colors" title="Horizontal Rule" aria-label="Horizontal rule">― Rule</button>

        <div className="mx-1 h-6 w-px bg-slate-300" />

        {/* Table controls */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setTableMenuOpen(!tableMenuOpen)}
            onBlur={() => setTimeout(() => setTableMenuOpen(false), 150)}
            className={`flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-sm font-medium transition-colors ${
              isInsideTable
                ? 'border-sky-300 bg-sky-50 text-sky-700'
                : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'
            }`}
            title="Table options"
            aria-expanded={tableMenuOpen}
            aria-haspopup="menu"
          >
            Table
            <svg className={`h-3.5 w-3.5 transition-transform ${tableMenuOpen ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" /></svg>
          </button>

          {tableMenuOpen && (
            <div className="absolute left-0 top-full z-50 mt-1 w-52 rounded-xl border border-slate-200 bg-white py-1 shadow-lg" role="menu">
              {!isInsideTable ? (
                <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
                  <span>Insert Table (3×3)</span>
                </button>
              ) : (
                <>
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Rows</div>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().addRowBefore().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">Add Row Above</button>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().addRowAfter().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">Add Row Below</button>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().deleteRow().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">Delete Row</button>
                  <div className="my-1 h-px bg-slate-100" />
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Columns</div>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().addColumnBefore().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">Add Column Left</button>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().addColumnAfter().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">Add Column Right</button>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().deleteColumn().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">Delete Column</button>
                  <div className="my-1 h-px bg-slate-100" />
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Merge</div>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().mergeCells().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">Merge Cells</button>
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().splitCell().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">Split Cell</button>
                  <div className="my-1 h-px bg-slate-100" />
                  <button type="button" role="menuitem" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().deleteTable().run(); setTableMenuOpen(false) }} className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">Delete Table</button>
                </>
              )}
            </div>
          )}
        </div>

        <div className="mx-1 h-6 w-px bg-slate-300" />

        {/* Undo/Redo */}
        <button type="button" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} className="rounded-lg px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-200 disabled:opacity-40 transition-colors" title="Undo (Ctrl+Z)" aria-label="Undo">Undo</button>
        <button type="button" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} className="rounded-lg px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-200 disabled:opacity-40 transition-colors" title="Redo (Ctrl+Y)" aria-label="Redo">Redo</button>

        {/* Snippets — pushed right */}
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
      Highlight.configure({ multicolor: false }),
      Subscript,
      Superscript,
      Link.configure({ openOnClick: false, HTMLAttributes: { class: 'text-sky-600 underline cursor-pointer' } }),
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
