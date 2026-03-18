import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Edit3, RefreshCw, Save, Send, X } from 'lucide-react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import DraftRecoveryNotice from '@/components/DraftRecoveryNotice'
import VersionDiffView from '@/components/VersionDiffView'
import { useFocusTrap } from '@/hooks/useAccessibility'
import {
  clearDraftRecovery,
  isDraftRecoveryDifferent,
  loadDraftRecovery,
  saveDraftRecovery,
} from '@/lib/draftRecovery'
import type { SectionEditTarget } from '@/pages/document-detail/helpers/previewHelpers'
import type { SectionSaveResult } from '@/pages/document-detail/hooks/useContentEditingFlow'
import { getDomParser } from '@/env/dom'

interface SectionEditPopupProps {
  documentId: number
  section: SectionEditTarget
  onClose: () => void
  onSave: (
    newHtml: string,
    submitForReview: boolean,
    options?: { force?: boolean; comparisonHtml?: string },
  ) => Promise<SectionSaveResult>
  onBack?: () => void
}

type ConflictState = Extract<SectionSaveResult, { status: 'conflict' }>
type EditingFrame = {
  editorHtml: string
  toPersistedHtml: (editorHtml: string) => string
}

function unwrapElement(element: Element): void {
  const parent = element.parentNode
  if (!parent) {
    return
  }

  while (element.firstChild) {
    parent.insertBefore(element.firstChild, element)
  }

  parent.removeChild(element)
}

function isStructuralEditingRoot(element: Element | null): element is HTMLElement {
  return (
    element instanceof HTMLElement &&
    element.matches('article.docx-document, div.pptx-presentation, section.pptx-slide')
  )
}

function createWrapperSerializer(root: HTMLElement): (editorHtml: string) => string {
  const tagName = root.tagName.toLowerCase()
  const attributes = Array.from(root.attributes).map((attribute) => ({
    name: attribute.name,
    value: attribute.value,
  }))

  return (editorHtml: string) => {
    const parser = getDomParser()
    const doc = parser.parseFromString('', 'text/html')
    const wrapper = doc.createElement(tagName)
    attributes.forEach((attribute) => {
      wrapper.setAttribute(attribute.name, attribute.value)
    })
    wrapper.innerHTML = editorHtml
    doc.body.appendChild(wrapper)
    return doc.body.innerHTML
  }
}

function createEditingFrame(html: string): EditingFrame {
  const parser = getDomParser()
  const doc = parser.parseFromString(html || '', 'text/html')
  const structuralRoot =
    doc.body.children.length === 1 && isStructuralEditingRoot(doc.body.firstElementChild)
      ? (doc.body.firstElementChild as HTMLElement)
      : null

  doc
    .querySelectorAll('div.table-wrapper, div.document-table-scroll')
    .forEach((element) => {
      unwrapElement(element)
    })

  if (structuralRoot) {
    return {
      editorHtml: structuralRoot.innerHTML,
      toPersistedHtml: createWrapperSerializer(structuralRoot),
    }
  }

  return {
    editorHtml: doc.body.innerHTML,
    toPersistedHtml: (editorHtml: string) => editorHtml,
  }
}

export function SectionEditPopup({
  documentId,
  section,
  onClose,
  onSave,
  onBack,
}: SectionEditPopupProps) {
  const initialEditingFrame = useMemo(() => createEditingFrame(section.html), [section.html])
  const { containerRef: dialogRef, handleKeyDown: trapKeyDown } = useFocusTrap(onClose)
  const [editingFrame, setEditingFrame] = useState(initialEditingFrame)
  const [isSaving, setIsSaving] = useState(false)
  const [submitForReview, setSubmitForReview] = useState(true)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [baselineHtml, setBaselineHtml] = useState(initialEditingFrame.editorHtml)
  const [comparisonHtml, setComparisonHtml] = useState<string | null>(null)
  const [restorableDraftSavedAt, setRestorableDraftSavedAt] = useState<string | null>(null)
  const [conflictState, setConflictState] = useState<ConflictState | null>(null)
  const hasPendingRecoveredDraftRef = useRef(false)

  const draftRecoveryTarget = useMemo(
    () => ({
      documentId,
      sectionId: section.id,
      editMode: section.editMode,
    }),
    [documentId, section.editMode, section.id],
  )

  useEffect(() => {
    setEditingFrame(initialEditingFrame)
    setBaselineHtml(initialEditingFrame.editorHtml)
  }, [initialEditingFrame])

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
    content: editingFrame.editorHtml,
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[200px] p-4',
      },
    },
  })

  useEffect(() => {
    if (!editor) {
      return
    }

    const recoveredDraft = loadDraftRecovery(draftRecoveryTarget)
    if (recoveredDraft && isDraftRecoveryDifferent(recoveredDraft.html, baselineHtml)) {
      hasPendingRecoveredDraftRef.current = true
      setRestorableDraftSavedAt(recoveredDraft.savedAt)
      return
    }

    hasPendingRecoveredDraftRef.current = false
    setRestorableDraftSavedAt(null)
  }, [baselineHtml, draftRecoveryTarget, editor])

  useEffect(() => {
    if (!editor) {
      return
    }

    let isInitialPersist = true
    const persistDraft = () => {
      const currentHtml = editor.getHTML()

      if (
        isInitialPersist &&
        hasPendingRecoveredDraftRef.current &&
        !isDraftRecoveryDifferent(currentHtml, baselineHtml)
      ) {
        isInitialPersist = false
        return
      }
      isInitialPersist = false

      if (isDraftRecoveryDifferent(currentHtml, baselineHtml)) {
        saveDraftRecovery(draftRecoveryTarget, {
          html: currentHtml,
          baseHtml: baselineHtml,
          savedAt: new Date().toISOString(),
        })
        return
      }

      clearDraftRecovery(draftRecoveryTarget)
    }

    persistDraft()
    editor.on('update', persistDraft)

    return () => {
      editor.off('update', persistDraft)
    }
  }, [baselineHtml, draftRecoveryTarget, editor])

  const handleRestoreDraft = () => {
    if (!editor) {
      return
    }

    const recoveredDraft = loadDraftRecovery(draftRecoveryTarget)
    if (!recoveredDraft) {
      setRestorableDraftSavedAt(null)
      return
    }

    editor.commands.setContent(recoveredDraft.html)
    hasPendingRecoveredDraftRef.current = false
    setRestorableDraftSavedAt(null)
    setConflictState(null)
    setSaveError(null)
  }

  const handleDismissDraft = () => {
    hasPendingRecoveredDraftRef.current = false
    clearDraftRecovery(draftRecoveryTarget)
    setRestorableDraftSavedAt(null)
  }

  const handleSave = async () => {
    if (!editor) return
    setIsSaving(true)
    setSaveError(null)
    try {
      const persistedHtml = editingFrame.toPersistedHtml(editor.getHTML())
      const result = await onSave(persistedHtml, submitForReview, {
        comparisonHtml: comparisonHtml ?? undefined,
      })
      if (result.status === 'conflict') {
        setConflictState(result)
        return
      }

      hasPendingRecoveredDraftRef.current = false
      clearDraftRecovery(draftRecoveryTarget)
      onClose()
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Failed to save section')
    } finally {
      setIsSaving(false)
    }
  }

  const handleForceSaveAfterConflict = async () => {
    if (!editor) {
      return
    }

    setIsSaving(true)
    setSaveError(null)
    try {
      const persistedHtml = editingFrame.toPersistedHtml(editor.getHTML())
      const result = await onSave(persistedHtml, submitForReview, {
        force: true,
        comparisonHtml: comparisonHtml ?? undefined,
      })
      if (result.status === 'conflict') {
        setConflictState(result)
        return
      }

      hasPendingRecoveredDraftRef.current = false
      clearDraftRecovery(draftRecoveryTarget)
      onClose()
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Failed to save section')
    } finally {
      setIsSaving(false)
    }
  }

  const handleUseLiveVersion = () => {
    if (!editor || !conflictState) {
      return
    }

    const liveEditingFrame = createEditingFrame(conflictState.liveEditorHtml)
    editor.commands.setContent(liveEditingFrame.editorHtml)
    setEditingFrame(liveEditingFrame)
    setBaselineHtml(liveEditingFrame.editorHtml)
    setComparisonHtml(conflictState.liveDocumentHtml)
    hasPendingRecoveredDraftRef.current = false
    clearDraftRecovery(draftRecoveryTarget)
    setConflictState(null)
    setRestorableDraftSavedAt(null)
    setSaveError(null)
  }

  const popupTitle =
    section.editMode === 'insert'
      ? 'Add New Section'
      : section.editMode === 'full'
        ? section.text && section.text !== 'Document Content'
          ? `Edit Document Content: ${section.text}`
          : 'Edit Document Content'
        : `Edit Section: ${section.text}`

  const showTableControls = true

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label={popupTitle} className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()} onKeyDown={trapKeyDown}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div className="flex items-center gap-3">
            <Edit3 className="w-5 h-5 text-white" />
            <h2 className="text-lg font-display font-semibold text-white">{popupTitle}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
            aria-label="Close editor"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {restorableDraftSavedAt && (
          <div className="px-6 pt-6">
            <DraftRecoveryNotice
              savedAt={restorableDraftSavedAt}
              onRestore={handleRestoreDraft}
              onDismiss={handleDismissDraft}
            />
          </div>
        )}

        {saveError && (
          <div className="px-6 pt-6">
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {saveError}
            </div>
          </div>
        )}

        {editor && (
          <div className="flex flex-wrap gap-1 p-2 border-b border-slate-200 bg-slate-50">
            <button
              onClick={() => editor.chain().focus().toggleBold().run()}
              aria-label="Bold"
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('bold') ? 'bg-slate-200' : ''
              }`}
              title="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleItalic().run()}
              aria-label="Italic"
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('italic') ? 'bg-slate-200' : ''
              }`}
              title="Italic"
            >
              <em>I</em>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              aria-label="Underline"
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
              aria-label="Heading 2"
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('heading', { level: 2 }) ? 'bg-slate-200' : ''
              }`}
              title="Heading 2"
            >
              H2
            </button>
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              aria-label="Heading 3"
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
              aria-label="Bullet List"
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('bulletList') ? 'bg-slate-200' : ''
              }`}
              title="Bullet List"
            >
              List
            </button>
            <button
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              aria-label="Numbered List"
              className={`p-2 rounded hover:bg-slate-200 ${
                editor.isActive('orderedList') ? 'bg-slate-200' : ''
              }`}
              title="Numbered List"
            >
              1. List
            </button>
            {showTableControls && (
              <>
                <div className="w-px bg-slate-300 mx-1" />
                <button
                  onClick={() =>
                    editor
                      .chain()
                      .focus()
                      .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
                      .run()
                  }
                  aria-label="Insert Table"
                  className="p-2 rounded hover:bg-slate-200"
                  title="Insert Table"
                >
                  Table
                </button>
                <button
                  onClick={() => editor.chain().focus().addRowAfter().run()}
                  aria-label="Add Table Row"
                  className="p-2 rounded hover:bg-slate-200"
                  title="Add Table Row"
                >
                  +Row
                </button>
                <button
                  onClick={() => editor.chain().focus().addColumnAfter().run()}
                  aria-label="Add Table Column"
                  className="p-2 rounded hover:bg-slate-200"
                  title="Add Table Column"
                >
                  +Col
                </button>
                <button
                  onClick={() => editor.chain().focus().deleteRow().run()}
                  aria-label="Delete Table Row"
                  className="p-2 rounded hover:bg-slate-200"
                  title="Delete Table Row"
                >
                  -Row
                </button>
                <button
                  onClick={() => editor.chain().focus().deleteColumn().run()}
                  aria-label="Delete Table Column"
                  className="p-2 rounded hover:bg-slate-200"
                  title="Delete Table Column"
                >
                  -Col
                </button>
                <button
                  onClick={() => editor.chain().focus().deleteTable().run()}
                  aria-label="Delete Table"
                  className="p-2 rounded hover:bg-slate-200"
                  title="Delete Table"
                >
                  Del Table
                </button>
              </>
            )}
          </div>
        )}

        {section.editMode === 'full' && (
          <div className="border-b border-slate-200 bg-sky-50 px-6 py-3 text-sm text-slate-700">
            {section.text && section.text !== 'Document Content'
              ? `This TOC item does not map to a standalone editable block, so editing opened the full document around "${section.text}".`
              : 'Full document mode keeps complex content editable in one place, including tables and mixed layout blocks.'}
          </div>
        )}

        <div className="flex-1 overflow-auto bg-white">
          <EditorContent editor={editor} className="min-h-[300px]" />
        </div>

        {conflictState && (
          <div className="border-t border-slate-200 bg-slate-50 px-6 py-6">
            <div className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-700" />
                <div>
                  <p className="font-semibold">Concurrent edits detected</p>
                  <p className="mt-1 text-amber-800">
                    The live document changed while you were editing. Review the diff below, then choose whether to keep your draft or refresh from the latest live content.
                  </p>
                </div>
              </div>
            </div>

            <VersionDiffView
              leftHtml={conflictState.liveDocumentHtml}
              rightHtml={conflictState.draftDocumentHtml}
              leftLabel="Live version"
              rightLabel="Your draft"
            />

            <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setConflictState(null)}
                className="btn-ghost"
              >
                Continue editing
              </button>
              <button
                type="button"
                onClick={handleUseLiveVersion}
                className="btn-secondary inline-flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Use live version
              </button>
              <button
                type="button"
                onClick={handleForceSaveAfterConflict}
                disabled={isSaving}
                className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                {isSaving ? 'Saving...' : 'Keep my draft and save'}
              </button>
            </div>
          </div>
        )}

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
