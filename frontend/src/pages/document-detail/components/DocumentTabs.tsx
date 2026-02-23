type TabType = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

interface DocumentTabsProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}

export function DocumentTabs({ activeTab, onTabChange }: DocumentTabsProps) {
  return (
    <div className="border-b border-slate-200">
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
            {tab === 'preview' ? 'Preview' : tab}
          </button>
        ))}
      </nav>
    </div>
  )
}
