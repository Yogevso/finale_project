type TabType = 'preview' | 'details' | 'versions' | 'attachments'

interface DocumentTabsProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  counts: {
    versions: number
    attachments: number
  }
  isRevamp?: boolean
}

export function DocumentTabs({ activeTab, onTabChange, counts, isRevamp = false }: DocumentTabsProps) {
  const labels: Record<TabType, string> = {
    preview: 'Preview',
    details: 'Details',
    versions: `Versions (${counts.versions})`,
    attachments: `Attachments (${counts.attachments})`,
  }

  return (
    <div
      className={`document-detail-tabs ${
        isRevamp
          ? 'z-20 rounded-2xl border border-slate-200 bg-white/95 px-2 py-1.5 shadow-[0_10px_24px_-18px_rgba(15,23,42,0.45)] backdrop-blur'
          : 'surface-muted p-1.5'
      }`}
    >
      <nav className={`flex flex-wrap ${isRevamp ? 'gap-1.5' : 'gap-1'}`}>
        {(['preview', 'details', 'versions', 'attachments'] as TabType[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={`table-action-btn rounded-xl border font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'border-blue-200 bg-blue-50 text-blue-700 shadow-sm dark:border-blue-800 dark:bg-slate-950 dark:text-blue-200'
                : isRevamp
                  ? 'border-transparent text-slate-500 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-200'
                  : 'border-transparent text-slate-500 hover:bg-white/80 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-200'
            }`}
          >
            {labels[tab]}
          </button>
        ))}
      </nav>
    </div>
  )
}
