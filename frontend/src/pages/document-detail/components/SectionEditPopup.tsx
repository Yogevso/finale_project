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
import DOMPurify from 'dompurify'
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
    wrapper.innerHTML = DOMPurify.sanitize(editorHtml)
    doc.body.appendChild(wrapper)
    return doc.body.innerHTML
  }
}

function createEditingFrame(html: string): EditingFrame {
  const parser = getDomParser()
  const doc = parser.parseFromString(DOMPurify.sanitize(html || ''), 'text/html')
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
  const { containerRef: dialogRef } = useFocusTrap<HTMLDivElement>(onClose)
  const [editingFrame, setEditingFrame] = useState(initialEditingFrame)
  const [isSaving, setIsSaving] = useState(false)
  const [submitForReview, setSubmitForReview] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [baselineHtml, setBaselineHtml] = useState(initialEditingFrame.editorHtml)
  const [comparisonHtml, setComparisonHtml] = useState<string | null>(null)
  const [restorableDraftSavedAt, setRestorableDraftSavedAt] = useState<string | null>(null)
  const [autoSavedAt, setAutoSavedAt] = useState<string | null>(null)
  const [hasLocalDraft, setHasLocalDraft] = useState(false)
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
      setAutoSavedAt(recoveredDraft.savedAt)
      setHasLocalDraft(true)
      return
    }

    hasPendingRecoveredDraftRef.current = false
    setRestorableDraftSavedAt(null)
    setAutoSavedAt(null)
    setHasLocalDraft(false)
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
        const savedAt = new Date().toISOString()
        saveDraftRecovery(draftRecoveryTarget, {
          html: currentHtml,
          baseHtml: baselineHtml,
          savedAt,
        })
        setAutoSavedAt(savedAt)
        setHasLocalDraft(true)
        return
      }

      clearDraftRecovery(draftRecoveryTarget)
      setAutoSavedAt(null)
      setHasLocalDraft(false)
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
    setAutoSavedAt(recoveredDraft.savedAt)
    setHasLocalDraft(true)
    setConflictState(null)
    setSaveError(null)
  }

  const handleDismissDraft = () => {
    hasPendingRecoveredDraftRef.current = false
    clearDraftRecovery(draftRecoveryTarget)
    setRestorableDraftSavedAt(null)
    setAutoSavedAt(null)
    setHasLocalDraft(false)
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
      setAutoSavedAt(null)
      setHasLocalDraft(false)
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
      setAutoSavedAt(null)
      setHasLocalDraft(false)
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
    setAutoSavedAt(null)
    setHasLocalDraft(false)
    setConflictState(null)
    setRestorableDraftSavedAt(null)
    setSaveError(null)
  }

  useEffect(() => {
    if (!hasLocalDraft) {
      return
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [hasLocalDraft])

  const popupTitle =
    section.editMode === 'insert'
      ? 'Add New Section'
      : section.editMode === 'full'
        ? section.text && section.text !== 'Document Content'
          ? `Edit Document Content: ${section.text}`
          : 'Edit Document Content'
        : `Edit Section: ${section.text}`

  const showTableControls = true
  const toolbarButtonClassName =
    'inline-flex h-9 min-w-9 items-center justify-center rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900'

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-transparent"
        onClick={onClose}
        aria-label="Close section editor"
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={popupTitle}
        tabIndex={-1}
        className="modal-content relative z-10 flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden"
      >
        <div className="flex items-center justify-between border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700 px-6 py-4">
          <div className="flex items-center gap-3">
            <Edit3 className="w-5 h-5 text-white" />
            <h2 className="section-title text-xl !text-white">{popupTitle}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-icon h-9 w-9 border-white/20 bg-white/10 text-white hover:bg-white/20 hover:text-white"
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
            <div className="alert-danger body-copy">
              {saveError}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-3 text-sm text-slate-600">
          <span>
            Local autosave keeps your draft in this browser until you save or dismiss it.
          </span>
          <span data-testid="local-autosave-status">
            {autoSavedAt ? `Auto-saved locally at ${new Date(autoSavedAt).toLocaleTimeString()}` : 'No local draft yet'}
          </span>
        </div>

        {editor && (
          <div className="surface-muted flex flex-wrap gap-1 rounded-none border-0 border-b border-slate-200 p-2">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBold().run()}
              aria-label="Bold"
              className={`${toolbarButtonClassName} ${
                editor.isActive('bold') ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleItalic().run()}
              aria-label="Italic"
              className={`${toolbarButtonClassName} ${
                editor.isActive('italic') ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Italic"
            >
              <em>I</em>
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              aria-label="Underline"
              className={`${toolbarButtonClassName} ${
                editor.isActive('underline') ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Underline"
            >
              <span className="underline">U</span>
            </button>
            <div className="w-px bg-slate-300 mx-1" />
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              aria-label="Heading 2"
              className={`${toolbarButtonClassName} ${
                editor.isActive('heading', { level: 2 }) ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Heading 2"
            >
              H2
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              aria-label="Heading 3"
              className={`${toolbarButtonClassName} ${
                editor.isActive('heading', { level: 3 }) ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Heading 3"
            >
              H3
            </button>
            <div className="w-px bg-slate-300 mx-1" />
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              aria-label="Bullet List"
              className={`${toolbarButtonClassName} ${
                editor.isActive('bulletList') ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Bullet List"
            >
              List
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              aria-label="Numbered List"
              className={`${toolbarButtonClassName} ${
                editor.isActive('orderedList') ? 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200' : ''
              }`}
              title="Numbered List"
            >
              1. List
            </button>
            {showTableControls && (
              <>
                <div className="w-px bg-slate-300 mx-1" />
                <button
                  type="button"
                  onClick={() =>
                    editor
                      .chain()
                      .focus()
                      .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
                      .run()
                  }
                  aria-label="Insert Table"
                  className={toolbarButtonClassName}
                  title="Insert Table"
                >
                  Table
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().addRowAfter().run()}
                  aria-label="Add Table Row"
                  className={toolbarButtonClassName}
                  title="Add Table Row"
                >
                  +Row
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().addColumnAfter().run()}
                  aria-label="Add Table Column"
                  className={toolbarButtonClassName}
                  title="Add Table Column"
                >
                  +Col
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().deleteRow().run()}
                  aria-label="Delete Table Row"
                  className={toolbarButtonClassName}
                  title="Delete Table Row"
                >
                  -Row
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().deleteColumn().run()}
                  aria-label="Delete Table Column"
                  className={toolbarButtonClassName}
                  title="Delete Table Column"
                >
                  -Col
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().deleteTable().run()}
                  aria-label="Delete Table"
                  className={toolbarButtonClassName}
                  title="Delete Table"
                >
                  Del Table
                </button>
              </>
            )}
          </div>
        )}

        {section.editMode === 'full' && (
          <div className="alert-info rounded-none border-x-0 border-t-0 px-6 py-3">
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
                className="btn-ghost table-action-btn"
              >
                Continue editing
              </button>
              <button
                type="button"
                onClick={handleUseLiveVersion}
                className="btn-secondary table-action-btn inline-flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Use live version
              </button>
              <button
                type="button"
                onClick={handleForceSaveAfterConflict}
                disabled={isSaving}
                className="btn-primary table-action-btn inline-flex items-center gap-2 disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                {isSaving ? 'Saving...' : 'Keep my draft and save'}
              </button>
            </div>
          </div>
        )}

        <div className="surface-muted flex items-center justify-between rounded-none border-0 border-t border-slate-200 px-6 py-4">
          <div className="body-copy">
            <label className="flex cursor-pointer items-center gap-2">
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
            <p className="helper-copy ml-6 mt-1">
              An admin/manager will review and approve your changes
            </p>
          </div>
          <div className="flex gap-3">
            {onBack && (
              <button type="button" onClick={onBack} className="btn-ghost table-action-btn">
                Back
              </button>
            )}
            <button type="button" onClick={onClose} className="btn-ghost table-action-btn">
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="btn-primary table-action-btn flex items-center gap-2 disabled:opacity-50"
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
