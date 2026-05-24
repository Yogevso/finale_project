import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowRight, Edit3, Save, Send, ShieldAlert, X } from 'lucide-react'
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
  saveDisabled?: boolean
  saveDisabledReason?: string
  reviewsLinkTo?: string
}

type EditingFrame = {
  editorHtml: string
  toPersistedHtml: (editorHtml: string) => string
}

type SectionSaveApiError = {
  response?: {
    status?: number
    data?: {
      detail?: unknown
      message?: unknown
      error_code?: unknown
    }
  }
  message?: unknown
}

const extractErrorText = (value: unknown): string | null => {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : null
  }

  if (value && typeof value === 'object') {
    const nested = value as {
      detail?: unknown
      message?: unknown
      error?: unknown
    }
    return (
      extractErrorText(nested.detail) ||
      extractErrorText(nested.message) ||
      extractErrorText(nested.error)
    )
  }

  return null
}

const getSectionSaveErrorMessage = (error: unknown): string => {
  const apiError = error as SectionSaveApiError
  const status = apiError.response?.status
  const errorCode = apiError.response?.data?.error_code
  const detail =
    extractErrorText(apiError.response?.data?.detail) ||
    extractErrorText(apiError.response?.data?.message) ||
    extractErrorText(apiError.message)

  const detailLower = detail?.toLowerCase() ?? ''
  const isPendingReviewConflict =
    status === 409 &&
    (errorCode === 'conflict' ||
      detailLower.includes('review is pending') ||
      detailLower.includes('while a review is pending'))

  if (isPendingReviewConflict) {
    return (
      'Cannot save while this document has a pending review. ' +
      'Ask a manager/admin to resolve the current review, then try again.'
    )
  }

  if (status === 401 || status === 403) {
    return (
      'Your session expired while saving. Your draft remains saved locally in this browser. ' +
      'Sign in again and retry.'
    )
  }

  return detail || 'Failed to save section'
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
  saveDisabled = false,
  saveDisabledReason,
  reviewsLinkTo = '/reviews',
}: SectionEditPopupProps) {
  const initialEditingFrame = useMemo(() => createEditingFrame(section.html), [section.html])
  const { containerRef: dialogRef } = useFocusTrap<HTMLDivElement>(onClose)
  const [editingFrame, setEditingFrame] = useState(initialEditingFrame)
  const [isSaving, setIsSaving] = useState(false)
  const [submitForReview, setSubmitForReview] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [baselineHtml, setBaselineHtml] = useState(initialEditingFrame.editorHtml)
  const [restorableDraftSavedAt, setRestorableDraftSavedAt] = useState<string | null>(null)
  const [autoSavedAt, setAutoSavedAt] = useState<string | null>(null)
  const [hasLocalDraft, setHasLocalDraft] = useState(false)
  const hasPendingRecoveredDraftRef = useRef(false)
  const resolvedSaveDisabledReason =
    saveDisabledReason?.trim() ||
    'This document has a pending review. Resolve it before creating a new draft.'

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
    if (!editor || saveDisabled) return
    setIsSaving(true)
    setSaveError(null)
    try {
      const persistedHtml = editingFrame.toPersistedHtml(editor.getHTML())
      let result = await onSave(persistedHtml, submitForReview)
      if (result.status === 'conflict') {
        result = await onSave(persistedHtml, submitForReview, {
          force: true,
          comparisonHtml: result.liveDocumentHtml,
        })
      }
      if (result.status === 'conflict') {
        throw new Error('Failed to save changes. Please try again.')
      }

      hasPendingRecoveredDraftRef.current = false
      clearDraftRecovery(draftRecoveryTarget)
      setAutoSavedAt(null)
      setHasLocalDraft(false)
      onClose()
    } catch (error) {
      setSaveError(getSectionSaveErrorMessage(error))
    } finally {
      setIsSaving(false)
    }
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
        <div className="flex items-center justify-between border-b border-slate-200 bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
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
            <div className="alert-danger body-copy" role="alert" aria-live="assertive">
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
                editor.isActive('bold') ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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
                editor.isActive('italic') ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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
                editor.isActive('underline') ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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
                editor.isActive('heading', { level: 2 }) ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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
                editor.isActive('heading', { level: 3 }) ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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
                editor.isActive('bulletList') ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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
                editor.isActive('orderedList') ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200' : ''
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

        <div className="surface-muted flex items-center justify-between rounded-none border-0 border-t border-slate-200 px-6 py-4">
          <div className="body-copy">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={submitForReview}
                onChange={(event) => setSubmitForReview(event.target.checked)}
                disabled={isSaving || saveDisabled}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span
                className={`flex items-center gap-2 ${saveDisabled ? 'opacity-60' : ''}`}
              >
                <Send className="w-4 h-4" />
                Submit for review after saving
              </span>
            </label>
            <p className="helper-copy ml-6 mt-1">
              An admin/manager will review and approve your changes
            </p>
            {saveDisabled && (
              <div className="ml-6 mt-2 rounded-xl border border-amber-200/80 bg-gradient-to-r from-amber-50 via-amber-50 to-white p-3 shadow-sm">
                <div className="flex flex-wrap items-start gap-3">
                  <span className="mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
                    <ShieldAlert className="h-4 w-4" />
                  </span>
                  <div className="min-w-[220px] flex-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                      Saving is temporarily locked
                    </p>
                    <p className="helper-copy mt-1 text-amber-700" role="status">
                      {resolvedSaveDisabledReason}
                    </p>
                  </div>
                  <a
                    href={reviewsLinkTo}
                    className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-amber-800 transition hover:border-amber-400 hover:bg-amber-100/40"
                  >
                    Open Reviews
                    <ArrowRight className="h-3.5 w-3.5" />
                  </a>
                </div>
              </div>
            )}
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
              disabled={isSaving || saveDisabled}
              title={saveDisabled ? resolvedSaveDisabledReason : undefined}
              className="btn-primary table-action-btn flex items-center gap-2 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSaving
                ? 'Saving...'
                : submitForReview
                  ? 'Save & Submit for Review'
                  : 'Save as Draft'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
