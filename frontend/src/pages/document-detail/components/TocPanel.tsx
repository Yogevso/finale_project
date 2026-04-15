import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { Check, ChevronDown, ChevronRight, Circle, Edit3, Link2, MoreVertical, Plus, Trash2 } from 'lucide-react'
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
}: TocPanelProps) {
  const [copiedSectionId, setCopiedSectionId] = useState<string | null>(null)
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null)
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set())
  const copiedTimeoutRef = useRef<number | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
    }
  }, [])

  // Close three-dot menu on outside click
  useEffect(() => {
    if (!menuOpenId) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenId(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpenId])

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
      className={`document-detail-toc-panel surface-muted rounded-none border-x-0 border-l-0 transition-all duration-300 ${
        tocCollapsed ? 'w-10' : 'w-72'
      } h-full flex flex-col flex-shrink-0 overflow-hidden`}
      data-tour="document-toc-panel"
    >
      <div className="sticky top-0 flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-slate-200 bg-white p-3 dark:bg-slate-950">
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
                activeSection ? 'text-sky-700' : 'text-slate-400'
              }`}
            >
              {activeSection?.text || 'Contents'}
            </span>
          </div>
        )}

        {!tocCollapsed && (
          <nav className="flex-1 h-0 overflow-y-auto p-2">
              {sections.length === 0 ? (
              <p className="body-copy px-2 py-2">No TOC available</p>
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
                            className="flex-shrink-0 h-6 w-5 flex items-center justify-center text-slate-400 hover:text-sky-600"
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
                          className={`flex-1 rounded-l px-1.5 py-1.5 text-left text-[13px] leading-5 transition-colors hover:bg-sky-50 hover:text-sky-700 ${
                            isActiveItem
                              ? 'bg-sky-100 text-sky-700 font-medium dark:bg-sky-950/40 dark:text-sky-200'
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

                        {/* Three-dot menu */}
                        {isEditor && !showingReaderView && (
                          <div className="relative flex-shrink-0" ref={menuOpenId === item.id ? menuRef : undefined}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                setMenuOpenId(menuOpenId === item.id ? null : item.id)
                              }}
                              className="btn-icon h-7 w-7 border-0 bg-transparent p-0 text-slate-400 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-slate-200 hover:text-slate-700"
                              title="Section actions"
                            >
                              <MoreVertical className="w-3.5 h-3.5" />
                            </button>

                            {menuOpenId === item.id && (
                              <div className="absolute right-0 top-full z-50 mt-1 w-40 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMenuOpenId(null)
                                    onEditSection(item)
                                  }}
                                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-700 dark:text-slate-200"
                                >
                                  <Edit3 className="h-3.5 w-3.5" />
                                  Edit
                                </button>
                                {onDeleteSection && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setMenuOpenId(null)
                                      onDeleteSection(item)
                                    }}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-rose-600 hover:bg-rose-50 dark:text-rose-400"
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                    Remove
                                  </button>
                                )}
                                <div className="mx-2 my-1 border-t border-slate-100 dark:border-slate-800" />
                                {onAddSectionAfter && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setMenuOpenId(null)
                                      onAddSectionAfter(sectionIdx)
                                    }}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-emerald-600 hover:bg-emerald-50 dark:text-emerald-400"
                                  >
                                    <Plus className="h-3.5 w-3.5" />
                                    Add Below
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMenuOpenId(null)
                                    void handleCopySectionLink(item)
                                  }}
                                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-700 dark:text-slate-200"
                                >
                                  <Link2 className="h-3.5 w-3.5" />
                                  Copy Link
                                </button>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Copy link (non-editor or reader view) */}
                        {(!isEditor || showingReaderView) && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation()
                              void handleCopySectionLink(item)
                            }}
                            className="btn-icon h-7 w-7 flex-shrink-0 border-0 bg-transparent p-0 text-sky-600 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-sky-100 hover:text-sky-700"
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

                      {/* Add section between items */}
                      {isEditor && !showingReaderView && onAddSectionAfter && (
                        <div className="relative h-0 overflow-visible opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            type="button"
                            onClick={() => onAddSectionAfter(sectionIdx)}
                            className="absolute left-1/2 -translate-x-1/2 -bottom-1 z-10 flex h-5 w-5 items-center justify-center rounded-full border border-emerald-300 bg-emerald-50 text-emerald-600 shadow-sm hover:bg-emerald-100 hover:shadow"
                            title="Add section here"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </nav>
        )}
      </div>
    </div>
  )
}
