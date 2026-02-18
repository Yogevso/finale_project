export interface PdfTocItem {
  id: string
  title: string
  level: number
  pageStart: number
}

interface PdfPreviewPanelProps {
  tocItems: PdfTocItem[]
  tocLoading: boolean
  tocError?: string | null
  selectedPage?: number | null
  onSelectItem: (item: PdfTocItem) => void
  iframeSrc?: string | null
  iframeKey: string
  iframeTitle: string
  heightClassName?: string
  containerClassName?: string
  onIframeError?: () => void
}

export default function PdfPreviewPanel({
  tocItems,
  tocLoading,
  tocError,
  selectedPage,
  onSelectItem,
  iframeSrc,
  iframeKey,
  iframeTitle,
  heightClassName = 'h-[70vh]',
  containerClassName = '',
  onIframeError,
}: PdfPreviewPanelProps) {
  return (
    <div className={`flex ${heightClassName} ${containerClassName}`.trim()}>
      <aside className="w-72 bg-slate-50 border-r border-slate-200 flex flex-col">
        <div className="px-4 py-3 border-b border-slate-200 bg-white">
          <h3 className="text-sm font-semibold text-slate-800">Contents</h3>
        </div>
        <div className="flex-1 overflow-y-auto">
          {tocLoading ? (
            <div className="p-4 text-sm text-slate-500">Loading TOC...</div>
          ) : tocItems.length > 0 ? (
            <nav className="p-2 space-y-1">
              {tocItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectItem(item)}
                  className={`w-full text-left px-2 py-1.5 text-sm rounded hover:bg-sky-100 hover:text-sky-800 ${
                    selectedPage === item.pageStart
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-700'
                  }`}
                  style={{ paddingLeft: `${Math.max(0, item.level - 1) * 14 + 8}px` }}
                >
                  <span className="truncate block">{item.title}</span>
                </button>
              ))}
            </nav>
          ) : (
            <div className="p-4 text-sm text-slate-500">{tocError || 'No TOC available'}</div>
          )}
        </div>
      </aside>
      <iframe
        key={iframeKey}
        src={iframeSrc || undefined}
        className="flex-1 h-full"
        title={iframeTitle}
        onError={onIframeError}
      />
    </div>
  )
}
