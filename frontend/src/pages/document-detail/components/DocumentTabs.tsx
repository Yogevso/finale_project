type TabType = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

interface DocumentTabsProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  counts: {
    versions: number
    attachments: number
    comments: number
  }
}

export function DocumentTabs({ activeTab, onTabChange, counts }: DocumentTabsProps) {
  const labels: Record<TabType, string> = {
    preview: 'Preview',
    details: 'Details',
    versions: `Versions (${counts.versions})`,
    attachments: `Attachments (${counts.attachments})`,
    comments: `Comments (${counts.comments})`,
  }

  return (
    <div className="document-detail-tabs border-b border-slate-200">
      <nav className="flex gap-6">
        {(['preview', 'details', 'versions', 'attachments', 'comments'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {labels[tab]}
          </button>
        ))}
      </nav>
    </div>
  )
}
