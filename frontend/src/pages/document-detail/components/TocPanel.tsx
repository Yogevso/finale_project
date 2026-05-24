import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { Check, ChevronDown, ChevronRight, Circle, Edit3, FilePlus2, Link2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { writeText } from '@/env/clipboard'
import { getWindowLocation } from '@/env/dom'
import { resolveSectionPageStart, type TocSection } from '@/pages/document-detail/helpers/previewHelpers'

interface TocPanelProps {
  sections: TocSection[]
  tocCollapsed: boolean
  onToggleCollapsed: () => void
  activeHeading: string | null
  readerCurrentPage: number | null
  isEditor?: boolean
  showingReaderView: boolean
  sectionLinkBasePath: string
  onSectionClick: (section: TocSection) => void
  onEditSection: (section: TocSection) => void
  onDeleteSection?: (section: TocSection) => void
  onAddSectionAfter?: (insertAfterIndex: number) => void
  isRevamp?: boolean
}

/** Compute hierarchical numbering like 1, 1.1, 1.2, 2, 2.1, 2.1.1 */
function computeSectionNumbers(sections: TocSection[]): string[] {
  const counters: number[] = []
  return sections.map((section) => {
    const level = section.level
    // Grow the counters array to match level
    while (counters.length < level) counters.push(0)
    // Truncate counters beyond current level
    counters.length = level
    // Increment current level counter
    counters[level - 1]++
    return counters.join('.')
  })
}

export function TocPanel({
  sections,
  tocCollapsed,
  onToggleCollapsed,
  activeHeading,
  readerCurrentPage,
  isEditor,
  showingReaderView,
  sectionLinkBasePath,
  onSectionClick,
  onEditSection,
  onDeleteSection,
  onAddSectionAfter,
  isRevamp = false,
}: TocPanelProps) {
  const [copiedSectionId, setCopiedSectionId] = useState<string | null>(null)
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set())
  const copiedTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
    }
  }, [])

  const sectionNumbers = useMemo(() => computeSectionNumbers(sections), [sections])

  const toggleCollapse = useCallback((sectionId: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev)
      if (next.has(sectionId)) {
        next.delete(sectionId)
      } else {
        next.add(sectionId)
      }
      return next
    })
  }, [])

  // Determine which sections are hidden because their parent is collapsed
  const visibleSections = useMemo(() => {
    const result: { section: TocSection; number: string; visible: boolean }[] = []
    let hiddenByParentId: string | null = null
    let hiddenByParentLevel = 0

    sections.forEach((section, idx) => {
      if (hiddenByParentId && section.level > hiddenByParentLevel) {
        result.push({ section, number: sectionNumbers[idx], visible: false })
      } else {
        hiddenByParentId = null
        result.push({ section, number: sectionNumbers[idx], visible: true })
        if (collapsedIds.has(section.id)) {
          hiddenByParentId = section.id
          hiddenByParentLevel = section.level
        }
      }
    })
    return result
  }, [sections, sectionNumbers, collapsedIds])

  const activeSection =
    sections.find((item) => {
      const anchorId = item.anchorId || `heading-${item.index}`
      const pageStart = resolveSectionPageStart(item)
      return activeHeading === anchorId || (!!pageStart && readerCurrentPage === pageStart)
    }) ?? sections[0]
  const activeSectionIndex = activeSection
    ? sections.findIndex((section) => section.id === activeSection.id)
    : -1

  const handleCopySectionLink = async (section: TocSection) => {
    const anchorId = section.anchorId || `heading-${section.index}`
    const sectionUrl = new URL(sectionLinkBasePath, getWindowLocation().origin)
    sectionUrl.hash = anchorId

    try {
      await writeText(sectionUrl.toString())
      setCopiedSectionId(section.id)
      toast.success('Section link copied')
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
      copiedTimeoutRef.current = window.setTimeout(() => setCopiedSectionId(null), 1600)
    } catch {
      toast.error('Failed to copy section link')
    }
  }

  // Check if a section has children (next section has higher level)
  const hasChildren = useCallback(
    (idx: number) => {
      const currentLevel = sections[idx].level
      return idx + 1 < sections.length && sections[idx + 1].level > currentLevel
    },
    [sections],
  )

  return (
    <div
      className={`document-detail-toc-panel transition-all duration-300 ${
        isRevamp
          ? `border-r border-slate-200 bg-slate-50/75 ${tocCollapsed ? 'w-12' : 'w-80'}`
          : `surface-muted rounded-none border-x-0 border-l-0 ${tocCollapsed ? 'w-10' : 'w-72'}`
      } h-full flex flex-col flex-shrink-0 overflow-hidden`}
      data-tour="document-toc-panel"
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <div
          className={`flex items-center justify-between border-b border-slate-200 p-3 dark:bg-slate-950 ${
            isRevamp ? 'bg-slate-100/80 backdrop-blur' : 'bg-white'
          }`}
        >
          {!tocCollapsed && (
            <h3 className="card-title flex items-center gap-2 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 10h16M4 14h16M4 18h16"
                />
              </svg>
              Contents
            </h3>
          )}
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="btn-icon h-8 w-8 border-0 bg-transparent text-slate-500 hover:bg-slate-200 hover:text-slate-700"
            title={tocCollapsed ? 'Expand' : 'Collapse'}
          >
            <svg
              className={`w-4 h-4 transition-transform ${tocCollapsed ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </button>
        </div>

        {tocCollapsed && (
          <div className="flex flex-1 items-center justify-center overflow-hidden px-1">
            <span
              className={`block max-w-[180px] origin-center -rotate-90 overflow-hidden text-ellipsis whitespace-nowrap text-[11px] font-semibold uppercase tracking-[0.18em] ${
                activeSection ? 'text-blue-700' : 'text-slate-400'
              }`}
            >
              {activeSection?.text || 'Contents'}
            </span>
          </div>
        )}

        {!tocCollapsed && (
          <>
            {isEditor && !showingReaderView && activeSection ? (
              <div className="border-b border-slate-200 bg-slate-50/90 px-2.5 py-2 dark:border-slate-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Section Actions
                </p>
                <p className="mt-1 truncate text-xs text-slate-600 dark:text-slate-300">
                  {activeSection.text}
                </p>
                <div className="mt-2 flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => onEditSection(activeSection)}
                    className="btn-icon h-7 w-7 border border-slate-200 bg-white text-slate-500 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                    title={`Edit ${activeSection.text}`}
                    aria-label={`Edit ${activeSection.text}`}
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                  </button>
                  {onDeleteSection && (
                    <button
                      type="button"
                      onClick={() => onDeleteSection(activeSection)}
                      className="btn-icon h-7 w-7 border border-slate-200 bg-white text-slate-500 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                      title={`Remove ${activeSection.text}`}
                      aria-label={`Remove ${activeSection.text}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {onAddSectionAfter && activeSectionIndex >= 0 && (
                    <button
                      type="button"
                      onClick={() => onAddSectionAfter(activeSectionIndex)}
                      className="btn-icon h-7 w-7 border border-slate-200 bg-white text-slate-500 hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                      title={`Add section below ${activeSection.text}`}
                      aria-label={`Add section below ${activeSection.text}`}
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void handleCopySectionLink(activeSection)}
                    className="btn-icon h-7 w-7 border border-slate-200 bg-white text-slate-500 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                    title={`Copy link to ${activeSection.text}`}
                    aria-label={`Copy link to ${activeSection.text}`}
                  >
                    {copiedSectionId === activeSection.id ? (
                      <Check className="w-3.5 h-3.5" />
                    ) : (
                      <Link2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>
            ) : null}

          <nav className={`flex-1 h-0 overflow-y-auto ${isRevamp ? 'p-2.5' : 'p-2'}`}>
            {sections.length === 0 ? (
              <div className="px-2 py-2">
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-3 text-center dark:border-slate-700 dark:bg-slate-900/40">
                  <span className="mx-auto inline-flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                    <FilePlus2 className="h-4 w-4" />
                  </span>
                  <p className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                    No sections yet
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Add the first section to start building the outline.
                  </p>
                </div>
                {isEditor && !showingReaderView && onAddSectionAfter && (
                  <button
                    type="button"
                    onClick={() => onAddSectionAfter(-1)}
                    className="mt-3 inline-flex items-center rounded-full border border-emerald-300 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-700 transition hover:border-emerald-400 hover:bg-emerald-50"
                  >
                    Add first section
                  </button>
                )}
              </div>
            ) : (
              <ul className="space-y-0.5">
                {visibleSections.map(({ section: item, number: sectionNumber, visible }) => {
                  if (!visible) return null
                  const anchorId = item.anchorId || `heading-${item.index}`
                  const pageStart = resolveSectionPageStart(item)
                  const isActiveItem =
                    activeHeading === anchorId || (!!pageStart && readerCurrentPage === pageStart)
                  const sectionIdx = sections.indexOf(item)
                  const canExpand = hasChildren(sectionIdx)
                  const isCollapsed = collapsedIds.has(item.id)

                  return (
                    <li key={item.id} className="group relative">
                      <div className="flex items-center gap-0.5">
                        {/* Expand/collapse toggle */}
                        {canExpand ? (
                          <button
                            type="button"
                            onClick={() => toggleCollapse(item.id)}
                            className="flex-shrink-0 h-6 w-5 flex items-center justify-center text-slate-400 hover:text-blue-600"
                            title={isCollapsed ? 'Expand' : 'Collapse'}
                          >
                            {isCollapsed ? (
                              <ChevronRight className="h-3.5 w-3.5" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5" />
                            )}
                          </button>
                        ) : (
                          <span className="flex-shrink-0 w-5 flex items-center justify-center">
                            {item.level >= 3 ? (
                              <span className="text-slate-300 text-xs">-</span>
                            ) : (
                              <Circle className="h-1.5 w-1.5 fill-current text-slate-300" />
                            )}
                          </span>
                        )}

                        {/* Section button with numbering */}
                        <button
                          type="button"
                          onClick={() => onSectionClick(item)}
                          title={item.text}
                          className={`flex-1 rounded-l px-1.5 py-1.5 text-left text-[13px] leading-5 transition-colors hover:bg-blue-50 hover:text-blue-700 ${
                            isActiveItem
                              ? 'bg-blue-100 text-blue-700 font-medium dark:bg-blue-950/40 dark:text-blue-200'
                              : 'text-slate-600 dark:text-slate-300'
                          }`}
                          style={{ paddingLeft: `${Math.max(0, (item.level - 1) * 8)}px` }}
                        >
                          <span className="flex items-start gap-1.5">
                            <span className="flex-shrink-0 font-mono text-[11px] text-slate-400 mt-[2px]">
                              {sectionNumber}
                            </span>
                            <span className="min-w-0 flex-1 whitespace-normal break-words">
                              {item.text}
                            </span>
                          </span>
                        </button>

                        {/* Copy link (non-editor or reader view) */}
                        {(!isEditor || showingReaderView) && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation()
                              void handleCopySectionLink(item)
                            }}
                            className="btn-icon h-7 w-7 flex-shrink-0 border-0 bg-transparent p-0 text-blue-600 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-blue-100 hover:text-blue-700"
                            title="Copy link to section"
                          >
                            {copiedSectionId === item.id ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <Link2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </nav>
          </>
        )}
      </div>
    </div>
  )
}
