import type { AnalyticsTabConfig, AnalyticsTabType } from '../constants'

type AnalyticsTabsNavProps = {
  activeTab: AnalyticsTabType
  tabs: AnalyticsTabConfig[]
  onTabChange: (tab: AnalyticsTabType) => void
}

export function AnalyticsTabsNav({ activeTab, tabs, onTabChange }: AnalyticsTabsNavProps) {
  return (
    <div className="surface-card rounded-2xl">
      <div className="border-b border-slate-200">
        <nav className="flex -mb-px overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap ${
                  isActive
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                <Icon className="w-5 h-5" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>
    </div>
  )
}

