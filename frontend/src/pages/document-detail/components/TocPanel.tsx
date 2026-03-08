import { Edit3 } from 'lucide-react'
import { resolveSectionPageStart, type TocSection } from '@/pages/document-detail/helpers/previewHelpers'

interface TocPanelProps {
  sections: TocSection[]
  tocCollapsed: boolean
  onToggleCollapsed: () => void
  activeHeading: string | null
  readerCurrentPage: number | null
  isEditor?: boolean
  showingReaderView: boolean
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
  onSectionClick,
  onEditSection,
}: TocPanelProps) {
  return (
    <div
      className={`bg-slate-50 border-r border-slate-200 transition-all duration-300 ${
        tocCollapsed ? 'w-10' : 'w-56'
      } flex-shrink-0`}
      data-tour="document-toc-panel"
    >
      <div className="sticky top-0">
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

        {!tocCollapsed && (
          <nav className="p-2 overflow-y-auto" style={{ maxHeight: 'calc(70vh - 50px)' }}>
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
                          className={`flex-1 text-left px-2 py-1.5 text-sm rounded-l transition-colors hover:bg-sky-50 hover:text-sky-700 ${
                            isActiveItem
                              ? 'bg-sky-100 text-sky-700 font-medium'
                              : 'text-slate-600'
                          }`}
                          style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                        >
                          <span className="flex items-center gap-2">
                            {item.level === 1 && <span className="text-sky-500">?</span>}
                            {item.level === 2 && <span className="text-slate-400">?</span>}
                            {item.level >= 3 && <span className="text-slate-300">-</span>}
                            <span className="truncate">{item.text}</span>
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
