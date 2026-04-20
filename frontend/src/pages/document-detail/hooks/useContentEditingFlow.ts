import { useCallback, useEffect, useReducer, useState } from 'react'
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

export interface RemovedSection {
  id: string
  text: string
  html: string
  removedAt: string
}

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

function normalizeCompactHtml(value: string | null | undefined): string {
  return (value || '')
    .replace(/>\s+</g, '><')
    .replace(/\s+/g, ' ')
    .trim()
}

function ensureUniqueSectionAnchorId(params: {
  html: string
  existingAnchorIds: string[]
  preferredAnchorId?: string | null
}): { html: string; anchorId: string | null } {
  const parser = getDomParser()
  const doc = parser.parseFromString(params.html || '', 'text/html')
  const heading = doc.body.querySelector('h1, h2, h3, h4, h5, h6')
  if (!heading) {
    return {
      html: params.html,
      anchorId: null,
    }
  }

  const occupiedAnchorIds = new Set(
    params.existingAnchorIds
      .map((value) => value.trim())
      .filter((value) => value.length > 0),
  )
  const preferredAnchorId = (params.preferredAnchorId || '').trim()
  const currentAnchorId = (heading.getAttribute('id') || '').trim()
  const baseAnchorId =
    preferredAnchorId ||
    currentAnchorId ||
    `heading-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`

  let resolvedAnchorId = baseAnchorId
  let suffix = 2
  while (occupiedAnchorIds.has(resolvedAnchorId)) {
    resolvedAnchorId = `${baseAnchorId}-${suffix}`
    suffix += 1
  }

  heading.setAttribute('id', resolvedAnchorId)
  heading.classList.add('scroll-mt-4')
  return {
    html: doc.body.innerHTML,
    anchorId: resolvedAnchorId,
  }
}

function findSectionIndexInHtmlSections(
  htmlSections: TocSection[],
  referenceSection: TocSection | null | undefined,
  fallbackIndex: number,
): number {
  if (htmlSections.length === 0) {
    return -1
  }

  if (referenceSection?.anchorId) {
    const byAnchor = htmlSections.findIndex((section) => section.anchorId === referenceSection.anchorId)
    if (byAnchor >= 0) {
      return byAnchor
    }
  }

  const referenceText = normalizeSectionText(referenceSection?.text)
  if (referenceText) {
    const byLabel = htmlSections.findIndex(
      (section) =>
        normalizeSectionText(section.text) === referenceText &&
        (!referenceSection || section.level === referenceSection.level),
    )
    if (byLabel >= 0) {
      return byLabel
    }
  }

  const referenceHtml = normalizeCompactHtml(referenceSection?.html)
  if (referenceHtml) {
    const byHtml = htmlSections.findIndex(
      (section) => normalizeCompactHtml(section.html) === referenceHtml,
    )
    if (byHtml >= 0) {
      return byHtml
    }
  }

  if (fallbackIndex >= 0) {
    return Math.min(htmlSections.length - 1, fallbackIndex)
  }

  return -1
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
  const [removedSections, setRemovedSections] = useState<RemovedSection[]>([])
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

      const allAnchorIds = sections
        .map((section) => (section.anchorId || '').trim())
        .filter((anchorId) => anchorId.length > 0)
      const anchorIdsWithoutCurrent =
        editingSection.anchorId && editingSection.anchorId.trim()
          ? allAnchorIds.filter((anchorId) => anchorId !== editingSection.anchorId)
          : allAnchorIds
      const normalizedSection =
        editingSection.editMode === 'full'
          ? { html: newHtml, anchorId: null as string | null }
          : ensureUniqueSectionAnchorId({
              html: newHtml,
              existingAnchorIds:
                editingSection.editMode === 'insert' ? allAnchorIds : anchorIdsWithoutCurrent,
              preferredAnchorId:
                editingSection.editMode === 'insert' ? null : editingSection.anchorId,
            })
      const nextSectionHtml = normalizedSection.html
      const nextSectionAnchorId = normalizedSection.anchorId || editingSection.anchorId || null

      let newFullHtml = ''
      if (editingSection.editMode === 'insert') {
        const htmlSections = processHtmlIntoSections(activeHtmlContent || '').sections
        if (htmlSections.length === 0) {
          newFullHtml = nextSectionHtml
        } else {
          const insertAfterIndex = editingSection.insertAfterIndex ?? -1
          const afterSection = insertAfterIndex >= 0 ? sections[insertAfterIndex] : null
          const matchedHtmlIndex = findSectionIndexInHtmlSections(
            htmlSections,
            afterSection,
            insertAfterIndex,
          )
          const insertAt = Math.max(0, Math.min(htmlSections.length, matchedHtmlIndex + 1))
          const updatedSections = [...htmlSections]
          updatedSections.splice(insertAt, 0, {
            ...editingSection,
            html: nextSectionHtml,
            index: insertAt,
            anchorId: nextSectionAnchorId || undefined,
          })
          newFullHtml = updatedSections.map((section) => section.html).filter(Boolean).join('\n')
        }
      } else if (editingSection.index < 0 || editingSection.editMode === 'full') {
        newFullHtml = nextSectionHtml
      } else if (editingSection.replaceAnchorId && editingSection.replaceNodeCount && activeHtmlContent) {
        newFullHtml =
          replaceFragmentInDocumentHtml(activeHtmlContent, editingSection, nextSectionHtml) ||
          activeHtmlContent
      } else {
        newFullHtml = sections
          .map((section, idx) =>
            idx === editingSection.index
              ? {
                  ...section,
                  html: nextSectionHtml,
                  anchorId: nextSectionAnchorId || section.anchorId,
                }
              : section,
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
        `--- New content ---\n${nextSectionHtml.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${
          nextSectionHtml.length > 500 ? '...' : ''
        }`

      const version = await api.createVersion(documentId, {
        content: newFullHtml,
        changes_summary: changesSummary,
      })

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

  const handleDeleteSection = useCallback(
    async (section: TocSection) => {
      const htmlSections = processHtmlIntoSections(activeHtmlContent || '').sections
      const sectionIndex =
        htmlSections.length > 0
          ? findSectionIndexInHtmlSections(
              htmlSections,
              section,
              sections.findIndex((candidate) => candidate.id === section.id),
            )
          : sections.findIndex((candidate) => candidate.id === section.id)
      if (sectionIndex < 0) return

      const resolvedSection = htmlSections[sectionIndex] || section

      // Store in removed sections before deleting
      setRemovedSections((prev) => [
        ...prev,
        {
          id: resolvedSection.id,
          text: resolvedSection.text,
          html: resolvedSection.html,
          removedAt: new Date().toISOString(),
        },
      ])

      const remaining = htmlSections.length > 0
        ? htmlSections.filter((_, idx) => idx !== sectionIndex)
        : sections.filter((_, idx) => idx !== sectionIndex)
      const newFullHtml = remaining.map((s) => s.html).filter(Boolean).join('\n')

      const changesSummary =
        `Section removed: "${resolvedSection.text}"\n\n` +
        `--- Removed content ---\n${resolvedSection.html.replace(/<[^>]*>/g, ' ').trim().slice(0, 500)}${
          resolvedSection.html.length > 500 ? '...' : ''
        }`

      await api.createVersion(documentId, {
        content: newFullHtml,
        changes_summary: changesSummary,
      })

      applyProcessedHtml(newFullHtml)

      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.bff.documentDetailBundle(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
    },
    [activeHtmlContent, applyProcessedHtml, documentId, queryClient, sections],
  )

  const handleRestoreSection = useCallback(
    async (removedSection: RemovedSection) => {
      // Append the restored section at the end of the current content
      const currentHtml = sections.map((s) => s.html).join('\n')
      const newFullHtml = currentHtml + '\n' + removedSection.html

      const changesSummary = `Section restored: "${removedSection.text}"`

      await api.createVersion(documentId, {
        content: newFullHtml,
        changes_summary: changesSummary,
      })

      applyProcessedHtml(newFullHtml)
      setRemovedSections((prev) => prev.filter((s) => s.id !== removedSection.id))

      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.bff.documentDetailBundle(documentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
    },
    [applyProcessedHtml, documentId, queryClient, sections],
  )

  const clearRemovedSections = useCallback(() => {
    setRemovedSections([])
  }, [])

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
    handleDeleteSection,
    removedSections,
    handleRestoreSection,
    clearRemovedSections,
  }
}
