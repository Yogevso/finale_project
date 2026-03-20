type TabType = 'preview' | 'details' | 'versions' | 'attachments'

interface DocumentTabsProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  counts: {
    versions: number
    attachments: number
  }
}

export function DocumentTabs({ activeTab, onTabChange, counts }: DocumentTabsProps) {
  const labels: Record<TabType, string> = {
    preview: 'Preview',
    details: 'Details',
    versions: `Versions (${counts.versions})`,
    attachments: `Attachments (${counts.attachments})`,
  }

  return (
    <div className="document-detail-tabs surface-muted p-1.5">
      <nav className="flex flex-wrap gap-1">
        {(['preview', 'details', 'versions', 'attachments'] as TabType[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={`table-action-btn rounded-xl border font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'border-sky-200 bg-white text-sky-700 shadow-sm dark:border-sky-800 dark:bg-slate-950 dark:text-sky-200'
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
