import { useCallback, useEffect, useReducer } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  createInitialContentEditingMachineState,
  toSectionEditTarget,
  transitionContentEditingMachineState,
} from '@/features/documentDetail'
import { getDomParser } from '@/env/dom'
import { api } from '@/lib/api'
import { sanitizeHtmlForPreview } from '@/lib/htmlSanitizer'
import { queryKeys } from '@/lib/queryKeys'
import {
  findSectionMatchInRoot,
  getEditableHtmlRoot,
  getUsableVersionContent,
  processHtmlIntoSections,
  type SectionEditTarget,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers'

interface UseContentEditingFlowParams {
  documentId: number
  isEditor?: boolean
  contentEditRequestToken?: number
  showingReaderView: boolean
  activeHtmlContent: string | null
  isLoading: boolean
  sections: TocSection[]
  applyProcessedHtml: (html: string) => void
  onRequireInlineContent: () => void
}

export type SectionSaveResult =
  | { status: 'saved' }
  | {
      status: 'conflict'
      draftDocumentHtml: string
      liveDocumentHtml: string
      liveEditorHtml: string
    }

function normalizeComparableHtml(html: string | null | undefined): string {
  return processHtmlIntoSections(sanitizeHtmlForPreview(html || '')).html
    .replace(/>\s+</g, '><')
    .replace(/\s+/g, ' ')
    .trim()
}

async function getLatestDocumentHtml(documentId: number): Promise<string | null> {
  const versionsResponse = await api.getVersions(documentId)
  const versionsWithContent = versionsResponse.items.filter((version) =>
    Boolean(getUsableVersionContent(version.content)),
  )

  const publishedVersion = versionsWithContent
    .filter((version) => version.is_published)
    .sort(
      (left, right) =>
        new Date(right.published_at || right.created_at).getTime() -
        new Date(left.published_at || left.created_at).getTime(),
    )[0]
  const latestVersion = versionsWithContent.sort(
    (left, right) =>
      new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  )[0]
  let versionToShow = publishedVersion || latestVersion

  if (!versionToShow && versionsResponse.items.length > 0) {
    const prioritizedIds = [
      ...new Set([
        ...versionsResponse.items
          .filter((version) => version.is_published)
          .sort(
            (left, right) =>
              new Date(right.published_at || right.created_at).getTime() -
              new Date(left.published_at || left.created_at).getTime(),
          )
          .map((version) => version.id),
        ...versionsResponse.items
          .sort(
            (left, right) =>
              new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
          )
          .map((version) => version.id),
      ]),
    ]

    for (const versionId of prioritizedIds) {
      const fullVersion = await api.getVersion(documentId, versionId)
      if (getUsableVersionContent(fullVersion.content)) {
        versionToShow = fullVersion
        break
      }
    }
  }

  return getUsableVersionContent(versionToShow?.content)
}

function resolveLiveEditorHtml(
  editingSection: SectionEditTarget,
  liveDocumentHtml: string,
): string {
  if (editingSection.editMode === 'full' || editingSection.index < 0) {
    return liveDocumentHtml
  }

  if (editingSection.editMode === 'insert') {
    return editingSection.html
  }

  const liveSections = processHtmlIntoSections(liveDocumentHtml).sections
  const matchedSection =
    liveSections.find(
      (section) =>
        section.anchorId === editingSection.anchorId ||
        (section.text === editingSection.text && section.level === editingSection.level),
    ) || liveSections[editingSection.index]

  return matchedSection?.html || editingSection.html
}

function buildFullDocumentEditTarget(
  html: string,
  options?: { requestedSectionText?: string; fromChooser?: boolean },
): SectionEditTarget {
  return toSectionEditTarget(
    {
      id: 'document-content',
      text: options?.requestedSectionText || 'Document Content',
      level: 1,
      html,
      index: -1,
      anchorId: 'document-content-area',
    },
    {
      fromChooser: options?.fromChooser ?? false,
      forceMode: 'full',
    },
  )
}

function normalizeSectionText(value: string | null | undefined): string {
  return (value || '').trim().replace(/\s+/g, ' ').toLowerCase()
}

function resolveSectionMatchBounds(
  root: HTMLElement,
  sections: TocSection[],
  sectionIndex: number,
): { minTopLevelIndex: number; maxTopLevelIndex: number } {
  let minTopLevelIndex = -1
  for (let index = 0; index < sectionIndex; index += 1) {
    const match = findSectionMatchInRoot(root, sections[index], {
      minTopLevelIndex,
    })
    if (match) {
      minTopLevelIndex = match.topLevelIndex
    }
  }

  let maxTopLevelIndex = Number.POSITIVE_INFINITY
  for (let index = sectionIndex + 1; index < sections.length; index += 1) {
    const match = findSectionMatchInRoot(root, sections[index], {
      minTopLevelIndex,
    })
    if (match) {
      maxTopLevelIndex = match.topLevelIndex
      break
    }
  }

  return {
    minTopLevelIndex,
    maxTopLevelIndex,
  }
}

function buildFragmentEditTarget(
  section: TocSection,
  sections: TocSection[],
  documentHtml: string,
  options?: { fromChooser?: boolean },
): SectionEditTarget | null {
  const parser = getDomParser()
  const doc = parser.parseFromString(documentHtml || '', 'text/html')
  const root = getEditableHtmlRoot(doc)
  const topLevelElements = Array.from(root.children) as HTMLElement[]
  const matchedSectionIndex = sections.findIndex(
    (candidate) =>
      candidate.id === section.id ||
      (candidate.anchorId === section.anchorId && candidate.text === section.text),
  )
  const sectionPosition = matchedSectionIndex >= 0 ? matchedSectionIndex : Math.max(0, section.index)
  const { minTopLevelIndex, maxTopLevelIndex } = resolveSectionMatchBounds(
    root,
    sections,
    sectionPosition,
  )
  const currentMatch = findSectionMatchInRoot(root, section, {
    minTopLevelIndex,
    maxTopLevelIndex,
  })

  if (!currentMatch) {
    return null
  }

  const endIndex =
    Number.isFinite(maxTopLevelIndex) && maxTopLevelIndex > currentMatch.topLevelIndex
      ? maxTopLevelIndex
      : topLevelElements.length

  const selectedNodes = topLevelElements.slice(currentMatch.topLevelIndex, endIndex)
  if (selectedNodes.length === 0) {
    return null
  }

  const replaceAnchorId =
    selectedNodes[0].id ||
    `editable-fragment-${sectionPosition}-${normalizeSectionText(section.text).replace(/[^a-z0-9]+/g, '-') || 'section'}`
  selectedNodes[0].id = replaceAnchorId

  return {
    ...toSectionEditTarget(
      {
        ...section,
        html: selectedNodes.map((node) => node.outerHTML).join('\n'),
        anchorId: replaceAnchorId,
      },
      {
        fromChooser: options?.fromChooser ?? false,
      },
    ),
    replaceAnchorId,
    replaceStartIndex: currentMatch.topLevelIndex,
    replaceNodeCount: selectedNodes.length,
  }
}

function replaceFragmentInDocumentHtml(
  documentHtml: string,
  editingSection: SectionEditTarget,
  newHtml: string,
): string | null {
  if (!editingSection.replaceAnchorId || !editingSection.replaceNodeCount) {
    return null
  }

  const parser = getDomParser()
  const doc = parser.parseFromString(documentHtml || '', 'text/html')
  const root = getEditableHtmlRoot(doc)
  const topLevelElements = Array.from(root.children) as HTMLElement[]
  const startIndex =
    typeof editingSection.replaceStartIndex === 'number'
      ? editingSection.replaceStartIndex
      : topLevelElements.findIndex((element) => element.id === editingSection.replaceAnchorId)
  if (startIndex < 0) {
    return null
  }

  const insertionBoundary = topLevelElements[startIndex + editingSection.replaceNodeCount] || null
  for (let offset = 0; offset < editingSection.replaceNodeCount; offset += 1) {
    const node = topLevelElements[startIndex + offset]
    node?.remove()
  }

  const fragmentDoc = parser.parseFromString(newHtml || '', 'text/html')
  const newNodes = Array.from(fragmentDoc.body.childNodes)
  newNodes.forEach((node) => {
    root.insertBefore(doc.importNode(node, true), insertionBoundary)
  })

  return doc.body.innerHTML
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
  onRequireInlineContent,
}: UseContentEditingFlowParams) {
  const queryClient = useQueryClient()
  const [editingFlowState, dispatchEditingFlow] = useReducer(
    transitionContentEditingMachineState,
    undefined,
    createInitialContentEditingMachineState,
  )
  const showContentEditChooser = editingFlowState.phase === 'chooser'
  const editingSection = editingFlowState.editingSection
  const handledContentEditToken = editingFlowState.handledRequestToken

  useEffect(() => {
    if (!contentEditRequestToken || contentEditRequestToken === handledContentEditToken) {
      return
    }

    if (!isEditor) {
      dispatchEditingFlow({
        type: 'MARK_REQUEST_HANDLED',
        token: contentEditRequestToken,
      })
      return
    }

    // Reader mode is non-editable; switch back to the editable document content first.
    if (showingReaderView) {
      onRequireInlineContent()
      return
    }

    if (!activeHtmlContent || isLoading) {
      return
    }

    dispatchEditingFlow({
      type: 'OPEN_CHOOSER',
      token: contentEditRequestToken,
    })
  }, [
    activeHtmlContent,
    contentEditRequestToken,
    handledContentEditToken,
    isEditor,
    isLoading,
    onRequireInlineContent,
    showingReaderView,
  ])

  const handleCloseContentEditChooser = useCallback(() => {
    dispatchEditingFlow({ type: 'CLOSE_CHOOSER' })
  }, [])

  const handleStartEditingSection = useCallback((section: TocSection) => {
    if (!section.html.trim() && activeHtmlContent) {
      const fragmentTarget = buildFragmentEditTarget(section, sections, activeHtmlContent)
      if (fragmentTarget) {
        dispatchEditingFlow({
          type: 'START_EDITING',
          section: fragmentTarget,
        })
        return
      }

      dispatchEditingFlow({
        type: 'START_EDITING',
        section: buildFullDocumentEditTarget(activeHtmlContent, {
          requestedSectionText: section.text,
        }),
      })
      return
    }

    dispatchEditingFlow({
      type: 'START_EDITING',
      section: toSectionEditTarget(section),
    })
  }, [activeHtmlContent, sections])

  const handleChooseEditSection = useCallback((section: TocSection) => {
    if (!section.html.trim() && activeHtmlContent) {
      const fragmentTarget = buildFragmentEditTarget(section, sections, activeHtmlContent, {
        fromChooser: true,
      })
      if (fragmentTarget) {
        dispatchEditingFlow({
          type: 'START_EDITING',
          section: fragmentTarget,
        })
        return
      }

      dispatchEditingFlow({
        type: 'START_EDITING',
        section: buildFullDocumentEditTarget(activeHtmlContent, {
          requestedSectionText: section.text,
          fromChooser: true,
        }),
      })
      return
    }

    dispatchEditingFlow({
      type: 'START_EDITING',
      section: toSectionEditTarget(section, {
        fromChooser: true,
      }),
    })
  }, [activeHtmlContent, sections])

  const handleEditFullDocument = useCallback(() => {
    if (!activeHtmlContent) {
      return
    }

    dispatchEditingFlow({
      type: 'START_EDITING',
      section: buildFullDocumentEditTarget(activeHtmlContent, {
        fromChooser: true,
      }),
    })
  }, [activeHtmlContent])

  const handleChooseAddSection = useCallback(
    (insertAfterIndex: number) => {
      const neighbor = insertAfterIndex >= 0 ? sections[insertAfterIndex] : sections[0]
      const headingLevel = Math.min(6, Math.max(2, neighbor?.level || 2))
      const headingTag = `h${headingLevel}`
      const defaultTitle = 'New Section'
      const defaultHtml = `<${headingTag}>${defaultTitle}</${headingTag}><p>Write section content here.</p>`

      const insertTarget: SectionEditTarget = {
        ...toSectionEditTarget(
          {
            id: `insert-${Date.now()}-${insertAfterIndex}`,
            text: defaultTitle,
            level: headingLevel,
            html: defaultHtml,
            index: Math.max(0, insertAfterIndex + 1),
          },
          { fromChooser: true, forceMode: 'insert' },
        ),
        insertAfterIndex,
      }

      dispatchEditingFlow({
        type: 'START_EDITING',
        section: insertTarget,
      })
    },
    [sections],
  )

  const handleCloseSectionEdit = useCallback(() => {
    dispatchEditingFlow({ type: 'CLOSE_EDITING' })
  }, [])

  const handleBackToChooser = useCallback(() => {
    dispatchEditingFlow({ type: 'BACK_TO_CHOOSER' })
  }, [])

  const handleSaveSection = useCallback(
    async (
      newHtml: string,
      submitForReview: boolean,
      options?: { force?: boolean; comparisonHtml?: string },
    ): Promise<SectionSaveResult> => {
      if (!editingSection) {
        return { status: 'saved' }
      }

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
      } else if (editingSection.replaceAnchorId && editingSection.replaceNodeCount && activeHtmlContent) {
        newFullHtml =
          replaceFragmentInDocumentHtml(activeHtmlContent, editingSection, newHtml) || activeHtmlContent
      } else {
        newFullHtml = sections
          .map((section, idx) =>
            idx === editingSection.index ? { ...section, html: newHtml } : section,
          )
          .map((section) => section.html)
          .join('\n')
      }

      const latestDocumentHtml = await getLatestDocumentHtml(documentId)
      const baselineHtml = options?.comparisonHtml ?? activeHtmlContent ?? ''

      if (
        !options?.force &&
        latestDocumentHtml &&
        baselineHtml &&
        normalizeComparableHtml(latestDocumentHtml) !== normalizeComparableHtml(baselineHtml)
      ) {
        return {
          status: 'conflict',
          draftDocumentHtml: newFullHtml,
          liveDocumentHtml: latestDocumentHtml,
          liveEditorHtml: resolveLiveEditorHtml(editingSection, latestDocumentHtml),
        }
      }

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

      const latestDocument = await api.getDocument(documentId)
      const ifMatch = latestDocument.etag || String(latestDocument.row_version || '')
      await api.updateDocument(documentId, { status: 'draft' }, ifMatch)

      if (submitForReview) {
        const reviewActionLabel =
          editingSection.editMode === 'insert' ? 'Added section' : 'Edited section'
        await api.submitForReview(documentId, {
          version_id: version.id,
          message: `${reviewActionLabel}: "${editingSection.text}"`,
        })
      }

      applyProcessedHtml(newFullHtml)

      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.bff.documentDetailBundle(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
      return { status: 'saved' }
    },
    [activeHtmlContent, applyProcessedHtml, documentId, editingSection, queryClient, sections],
  )

  return {
    showContentEditChooser,
    editingSection,
    handleCloseContentEditChooser,
    handleStartEditingSection,
    handleEditFullDocument,
    handleChooseEditSection,
    handleChooseAddSection,
    handleCloseSectionEdit,
    handleBackToChooser,
    handleSaveSection,
  }
}
