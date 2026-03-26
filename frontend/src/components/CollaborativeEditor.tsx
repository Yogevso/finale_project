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
import { useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { CollaborationStatus } from './CollaborationStatus'
import { ReadOnlyBanner, PermissionIndicator } from './ReadOnlyBanner'
import type { CollaboratorInfo } from '@/lib/useCollaboration'
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
const MenuBar = ({ editor }: { editor: ReturnType<typeof useEditor> }) => {
  if (!editor) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-1 p-2 border-b border-slate-200 bg-slate-50">
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={`px-2 py-1 rounded-lg text-sm font-medium ${
          editor.isActive('bold') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Bold"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('italic') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Italic"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('underline') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Underline"
      >
        <u>U</u>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleStrike().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('strike') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Strikethrough"
      >
        <s>S</s>
      </button>

      <div className="w-px h-6 bg-slate-300 mx-1" />

      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('heading', { level: 1 }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Heading 1"
      >
        H1
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('heading', { level: 2 }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Heading 2"
      >
        H2
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('heading', { level: 3 }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Heading 3"
      >
        H3
      </button>

      <div className="w-px h-6 bg-slate-300 mx-1" />

      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('bulletList') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Bullet List"
      >
        • List
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('orderedList') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Numbered List"
      >
        1. List
      </button>

      <div className="w-px h-6 bg-slate-300 mx-1" />

      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive({ textAlign: 'left' }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Align Left"
      >
        ⬅
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive({ textAlign: 'center' }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Align Center"
      >
        ⬌
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive({ textAlign: 'right' }) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Align Right"
      >
        ➡
      </button>

      <div className="w-px h-6 bg-slate-300 mx-1" />

      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('blockquote') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Quote"
      >
        ""
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        className={`px-2 py-1 rounded-lg text-sm ${
          editor.isActive('codeBlock') ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-200'
        }`}
        title="Code Block"
      >
        {'</>'}
      </button>
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
