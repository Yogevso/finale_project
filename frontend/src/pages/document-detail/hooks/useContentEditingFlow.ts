import { useCallback, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'
import type { SectionEditTarget, TocSection } from '@/pages/document-detail/helpers/previewHelpers'

interface UseContentEditingFlowParams {
  documentId: number
  isEditor?: boolean
  contentEditRequestToken?: number
  showingReaderView: boolean
  activeHtmlContent: string | null
  isLoading: boolean
  sections: TocSection[]
  applyProcessedHtml: (html: string) => void
  onRequireOriginalPdf: () => void
}

export function useContentEditingFlow({
  documentId,
  isEditor,
  contentEditRequestToken = 0,
  showingReaderView,
  activeHtmlContent,
  isLoading,
  sections,
  applyProcessedHtml,
  onRequireOriginalPdf,
}: UseContentEditingFlowParams) {
  const queryClient = useQueryClient()
  const [showContentEditChooser, setShowContentEditChooser] = useState(false)
  const [editingSection, setEditingSection] = useState<SectionEditTarget | null>(null)
  const [handledContentEditToken, setHandledContentEditToken] = useState(0)

  useEffect(() => {
    if (!contentEditRequestToken || contentEditRequestToken === handledContentEditToken) {
      return
    }

    if (!isEditor) {
      setHandledContentEditToken(contentEditRequestToken)
      return
    }

    // Reader mode is non-editable; switch back to original first and continue on next render.
    if (showingReaderView) {
      onRequireOriginalPdf()
      return
    }

    if (!activeHtmlContent || isLoading) {
      return
    }

    setEditingSection(null)
    setShowContentEditChooser(true)
    setHandledContentEditToken(contentEditRequestToken)
  }, [
    activeHtmlContent,
    contentEditRequestToken,
    handledContentEditToken,
    isEditor,
    isLoading,
    onRequireOriginalPdf,
    showingReaderView,
  ])

  const handleCloseContentEditChooser = useCallback(() => {
    setShowContentEditChooser(false)
  }, [])

  const handleStartEditingSection = useCallback((section: TocSection) => {
    setEditingSection(section)
  }, [])

  const handleChooseEditSection = useCallback((section: TocSection) => {
    setShowContentEditChooser(false)
    setEditingSection({
      ...section,
      editMode: section.index < 0 ? 'full' : 'edit',
      fromChooser: true,
    })
  }, [])

  const handleChooseAddSection = useCallback(
    (insertAfterIndex: number) => {
      const neighbor = insertAfterIndex >= 0 ? sections[insertAfterIndex] : sections[0]
      const headingLevel = Math.min(6, Math.max(2, neighbor?.level || 2))
      const headingTag = `h${headingLevel}`
      const defaultTitle = 'New Section'
      const defaultHtml = `<${headingTag}>${defaultTitle}</${headingTag}><p>Write section content here.</p>`

      setShowContentEditChooser(false)
      setEditingSection({
        id: `insert-${Date.now()}-${insertAfterIndex}`,
        text: defaultTitle,
        level: headingLevel,
        html: defaultHtml,
        index: Math.max(0, insertAfterIndex + 1),
        editMode: 'insert',
        insertAfterIndex,
        fromChooser: true,
      })
    },
    [sections],
  )

  const handleCloseSectionEdit = useCallback(() => {
    setEditingSection(null)
  }, [])

  const handleBackToChooser = useCallback(() => {
    setEditingSection(null)
    setShowContentEditChooser(true)
  }, [])

  const handleSaveSection = useCallback(
    async (newHtml: string, submitForReview: boolean) => {
      if (!editingSection) return

      // Get old section content for comparison.
      const oldSectionHtml = editingSection.editMode === 'insert' ? '' : editingSection.html

      let newFullHtml = ''
      if (editingSection.editMode === 'insert') {
        const insertAt = Math.max(
          0,
          Math.min(sections.length, (editingSection.insertAfterIndex ?? -1) + 1),
        )
        const updatedSections = [...sections]
        updatedSections.splice(insertAt, 0, {
          ...editingSection,
          html: newHtml,
          index: insertAt,
        })
        newFullHtml = updatedSections.map((section) => section.html).join('\n')
      } else if (editingSection.index < 0 || editingSection.editMode === 'full') {
        newFullHtml = newHtml
      } else {
        newFullHtml = sections
          .map((section, idx) =>
            idx === editingSection.index ? { ...section, html: newHtml } : section,
          )
          .map((section) => section.html)
          .join('\n')
      }

      applyProcessedHtml(newFullHtml)

      const sectionAction = editingSection.editMode === 'insert' ? 'Section added' : 'Section edited'
      const oldContentSummary =
        editingSection.editMode === 'insert'
          ? 'N/A (new section)'
          : `${oldSectionHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${
              oldSectionHtml.length > 500 ? '...' : ''
            }`
      const changesSummary =
        `${sectionAction}: "${editingSection.text}"\n\n` +
        `--- Original content ---\n${oldContentSummary}\n\n` +
        `--- New content ---\n${newHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${
          newHtml.length > 500 ? '...' : ''
        }`

      const version = await api.createVersion(documentId, {
        content: newFullHtml,
        changes_summary: changesSummary,
      })

      await api.updateDocument(documentId, { status: 'draft' })

      if (submitForReview) {
        const reviewActionLabel =
          editingSection.editMode === 'insert' ? 'Added section' : 'Edited section'
        await api.submitForReview(documentId, {
          version_id: version.id,
          message: `${reviewActionLabel}: "${editingSection.text}"`,
        })
      }

      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
    },
    [applyProcessedHtml, documentId, editingSection, queryClient, sections],
  )

  return {
    showContentEditChooser,
    editingSection,
    handleCloseContentEditChooser,
    handleStartEditingSection,
    handleChooseEditSection,
    handleChooseAddSection,
    handleCloseSectionEdit,
    handleBackToChooser,
    handleSaveSection,
  }
}
