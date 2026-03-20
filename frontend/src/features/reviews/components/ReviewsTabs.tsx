import { Clock, Send } from 'lucide-react'

import type { ReviewsTabType } from '../constants'

type ReviewsTabsProps = {
  activeTab: ReviewsTabType
  pendingCount: number
  onTabChange: (tab: ReviewsTabType) => void
}

export function ReviewsTabs({ activeTab, pendingCount, onTabChange }: ReviewsTabsProps) {
  return (
    <div className="surface-card rounded-2xl px-4">
      <nav className="flex gap-4 border-b border-slate-200">
        <button
          type="button"
          onClick={() => onTabChange('pending')}
          className={`inline-flex items-center gap-2 border-b-2 px-2 py-3 text-sm font-medium transition-colors ${
            activeTab === 'pending'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Clock className="w-4 h-4" />
          Pending My Review
          {pendingCount > 0 ? <span className="pill bg-amber-100 text-amber-700">{pendingCount}</span> : null}
        </button>
        <button
          type="button"
          onClick={() => onTabChange('my-submissions')}
          className={`inline-flex items-center gap-2 border-b-2 px-2 py-3 text-sm font-medium transition-colors ${
            activeTab === 'my-submissions'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Send className="w-4 h-4" />
          My Submissions
        </button>
      </nav>
    </div>
  )
}
