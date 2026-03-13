import { useEffect, useRef, useState } from 'react'
import { Check, ChevronRight, Circle, Edit3, Link2 } from 'lucide-react'
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
}: TocPanelProps) {
  const [copiedSectionId, setCopiedSectionId] = useState<string | null>(null)
  const copiedTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
    }
  }, [])

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

  return (
    <div
      className={`document-detail-toc-panel bg-slate-50 border-r border-slate-200 transition-all duration-300 ${
        tocCollapsed ? 'w-10' : 'w-72'
      } h-full flex flex-col flex-shrink-0 overflow-hidden`}
      data-tour="document-toc-panel"
    >
      <div className="sticky top-0 flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-white">
          {!tocCollapsed && (
            <h3 className="font-medium text-sm text-slate-700 flex items-center gap-2">
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
            onClick={onToggleCollapsed}
            className="p-1 hover:bg-slate-200 rounded text-slate-500"
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
              <p className="px-2 py-2 text-sm text-slate-500">No TOC available</p>
            ) : (
              <ul className="space-y-1">
                {sections.map((item) => {
                  const anchorId = item.anchorId || `heading-${item.index}`
                  const pageStart = resolveSectionPageStart(item)
                  const isActiveItem =
                    activeHeading === anchorId || (!!pageStart && readerCurrentPage === pageStart)

                  return (
                    <li key={item.id} className="group">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => onSectionClick(item)}
                          title={item.text}
                          className={`flex-1 text-left px-2 py-1.5 text-sm rounded-l transition-colors hover:bg-sky-50 hover:text-sky-700 ${
                            isActiveItem
                              ? 'bg-sky-100 text-sky-700 font-medium'
                              : 'text-slate-600'
                          }`}
                          style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                        >
                          <span className="flex items-start gap-2">
                            {item.level === 1 && <ChevronRight className="h-3.5 w-3.5 text-sky-500" />}
                            {item.level === 2 && (
                              <Circle className="h-2.5 w-2.5 fill-current text-slate-400" />
                            )}
                            {item.level >= 3 && <span className="text-slate-300">-</span>}
                            <span className="min-w-0 flex-1 whitespace-normal break-words leading-5">
                              {item.text}
                            </span>
                          </span>
                        </button>

                        {isEditor && !showingReaderView && (
                          <button
                            onClick={() => onEditSection(item)}
                            className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-sky-100 rounded text-sky-600 transition-opacity"
                            title="Edit section"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation()
                            void handleCopySectionLink(item)
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-sky-100 rounded text-sky-600 transition-opacity"
                          title="Copy link to section"
                        >
                          {copiedSectionId === item.id ? (
                            <Check className="w-3.5 h-3.5" />
                          ) : (
                            <Link2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
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
