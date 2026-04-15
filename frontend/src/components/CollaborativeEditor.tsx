/**
 * CollaborativeEditor Component
 *
 * TipTap editor with real-time collaboration support via Yjs.
 * Shows collaborator cursors and syncs changes across clients.
 * Supports read-only mode for viewers with permission controls.
 */

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import Collaboration from '@tiptap/extension-collaboration'
import CollaborationCursor from '@tiptap/extension-collaboration-cursor'
import * as Y from 'yjs'
import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { CollaborationStatus } from './CollaborationStatus'
import { ReadOnlyBanner, PermissionIndicator } from './ReadOnlyBanner'
import type { CollaboratorInfo } from '@/lib/collaboration/types'
import type { HocuspocusProvider } from '@hocuspocus/provider'

interface CollaborativeEditorProps {
  // Collaboration props
  ydoc: Y.Doc | null
  provider: HocuspocusProvider | null
  isConnected: boolean
  isConnecting: boolean
  isSynced: boolean
  error: string | null
  persistenceWarning: string | null
  collaborators: CollaboratorInfo[]
  currentUser: {
    userId: string | number
    username: string
    color: string
  }

  // Permission props
  isReadOnly?: boolean
  permissions?: string[]
  onRefreshPermissions?: () => void
  onRequestAccess?: () => void

  // Editor props
  content?: string
  onChange?: (html: string) => void
  editable?: boolean
  className?: string
  onRetry?: () => void
}

// Menu bar component (same as RichTextEditor)
const COLLAB_BLOCK_FORMATS = [
  { id: 'paragraph', label: 'Normal Text', shortLabel: 'Normal', action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().setParagraph().run() },
  { id: 'h1', label: 'Title', shortLabel: 'H1 — Title', level: 1, action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().toggleHeading({ level: 1 }).run() },
  { id: 'h2', label: 'Section Title', shortLabel: 'H2 — Section Title', level: 2, action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().toggleHeading({ level: 2 }).run() },
  { id: 'h3', label: 'Sub-section Title', shortLabel: 'H3 — Sub-section', level: 3, action: (e: NonNullable<ReturnType<typeof useEditor>>) => e.chain().focus().toggleHeading({ level: 3 }).run() },
] as const

function getCollabActiveBlockFormat(editor: NonNullable<ReturnType<typeof useEditor>>) {
  if (editor.isActive('heading', { level: 1 })) return COLLAB_BLOCK_FORMATS[1]
  if (editor.isActive('heading', { level: 2 })) return COLLAB_BLOCK_FORMATS[2]
  if (editor.isActive('heading', { level: 3 })) return COLLAB_BLOCK_FORMATS[3]
  return COLLAB_BLOCK_FORMATS[0]
}

const MenuBar = ({ editor }: { editor: ReturnType<typeof useEditor> }) => {
  const [blockDropdownOpen, setBlockDropdownOpen] = useState(false)

  if (!editor) {
    return null
  }

  const activeBlock = getCollabActiveBlockFormat(editor)
  const isHeadingActive = activeBlock.id !== 'paragraph'

  return (
    <div className="flex flex-col border-b border-slate-200 bg-slate-50">
      <div className="flex flex-wrap items-center gap-1 p-2">
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
              {COLLAB_BLOCK_FORMATS.map((format) => {
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

        <div className="w-px h-6 bg-slate-300 mx-1" />

        {/* Inline formatting */}
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={`px-2 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            editor.isActive('bold') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Bold (Ctrl+B)"
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('italic') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Italic (Ctrl+I)"
        >
          <em>I</em>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('underline') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Underline (Ctrl+U)"
        >
          <u>U</u>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('strike') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Strikethrough"
        >
          <s>S</s>
        </button>

        <div className="w-px h-6 bg-slate-300 mx-1" />

        {/* Lists */}
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('bulletList') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Bullet List"
        >
          Bullets
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('orderedList') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Numbered List"
        >
          Numbers
        </button>

        <div className="w-px h-6 bg-slate-300 mx-1" />

        {/* Alignment */}
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign('left').run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive({ textAlign: 'left' }) ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Align Left"
        >
          Left
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign('center').run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive({ textAlign: 'center' }) ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Align Center"
        >
          Center
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setTextAlign('right').run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive({ textAlign: 'right' }) ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Align Right"
        >
          Right
        </button>

        <div className="w-px h-6 bg-slate-300 mx-1" />

        {/* Block formatting */}
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('blockquote') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Quote"
        >
          Quote
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className={`px-2 py-1.5 rounded-lg text-sm transition-colors ${
            editor.isActive('codeBlock') ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200' : 'text-slate-600 hover:bg-slate-200'
          }`}
          title="Code Block"
        >
          {'</>'}
        </button>
      </div>
    </div>
  )
}

export function CollaborativeEditor({
  ydoc,
  provider,
  isConnected,
  isConnecting,
  isSynced,
  error,
  persistenceWarning,
  collaborators,
  currentUser,
  isReadOnly = false,
  permissions = [],
  onRefreshPermissions,
  onRequestAccess,
  content,
  onChange,
  editable = true,
  className = '',
  onRetry,
}: CollaborativeEditorProps) {
  // Determine if the editor should be editable
  // isReadOnly from collaboration takes precedence
  const isEditable = editable && !isReadOnly

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable undoRedo when using Yjs - it handles undo/redo
        undoRedo: ydoc ? false : undefined,
      }),
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
      // Add collaboration extensions when connected
      ...(ydoc && provider
        ? [
            Collaboration.configure({
              document: ydoc,
            }),
            CollaborationCursor.configure({
              provider: provider,
              user: {
                name: currentUser.username,
                color: currentUser.color,
              },
            }),
          ]
        : []),
    ],
    content: ydoc ? undefined : content, // Use Yjs content when connected
    editable: isEditable,
    onUpdate: ({ editor }) => {
      if (onChange && !ydoc) {
        // Only call onChange when not in collab mode
        onChange(editor.getHTML())
      }
    },
  })

  // Set initial content when not in collaboration mode
  useEffect(() => {
    if (editor && !ydoc && content && content !== editor.getHTML()) {
      editor.commands.setContent(content)
    }
  }, [content, editor, ydoc])

  // Update editable state
  useEffect(() => {
    if (editor) {
      editor.setEditable(isEditable)
    }
  }, [isEditable, editor])

  return (
    <div className={`border border-slate-300 rounded-xl overflow-hidden ${className}`}>
      {/* Read-only banner for viewers */}
      <ReadOnlyBanner
        isReadOnly={isReadOnly}
        onRefreshPermissions={onRefreshPermissions}
        onRequestAccess={onRequestAccess}
      />

      {persistenceWarning && (
        <div
          className="flex items-center justify-between gap-3 border-b border-rose-200 bg-rose-50 px-4 py-3"
          role="alert"
          aria-live="assertive"
        >
          <div className="flex items-start gap-2 text-rose-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Server saving failed</p>
              <p className="text-sm">{persistenceWarning}</p>
            </div>
          </div>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="shrink-0 rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-rose-700"
            >
              Reconnect
            </button>
          )}
        </div>
      )}

      {/* Toolbar with collaboration status */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50">
        <div className="flex-1">
          {isEditable && <MenuBar editor={editor} />}
          {!isEditable && (
            <div className="px-3 py-2 text-sm text-slate-500 italic">
              Editing disabled — view only mode
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 px-3 py-2 border-l border-slate-200">
          {permissions.length > 0 && (
            <PermissionIndicator permissions={permissions} />
          )}
          <CollaborationStatus
            isConnected={isConnected}
            isConnecting={isConnecting}
            isSynced={isSynced}
            error={error}
            collaborators={collaborators}
            onRetry={onRetry}
          />
        </div>
      </div>

      {/* Editor Content */}
      <EditorContent
        editor={editor}
        className={`prose max-w-none p-4 min-h-[400px] focus:outline-none ${
          isEditable ? 'bg-white' : 'bg-slate-50 cursor-not-allowed'
        }`}
      />

      {/* Collaboration cursor styles */}
      <style>{`
        .collaboration-cursor__caret {
          position: relative;
          margin-left: -1px;
          margin-right: -1px;
          border-left: 1px solid;
          border-right: 1px solid;
          word-break: normal;
          pointer-events: none;
        }

        .collaboration-cursor__label {
          position: absolute;
          top: -1.4em;
          left: -1px;
          font-size: 12px;
          font-style: normal;
          font-weight: 600;
          line-height: normal;
          user-select: none;
          color: white;
          padding: 0.1rem 0.3rem;
          border-radius: 3px 3px 3px 0;
          white-space: nowrap;
        }
      `}</style>
    </div>
  )
}

export default CollaborativeEditor
