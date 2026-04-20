import { Clock, Send } from 'lucide-react';

import type { ReviewsTabType } from '../constants';

type ReviewsTabsProps = {
  activeTab: ReviewsTabType;
  pendingCount: number;
  onTabChange: (tab: ReviewsTabType) => void;
};

export function ReviewsTabs({ activeTab, pendingCount, onTabChange }: ReviewsTabsProps) {
  const pendingActive = activeTab === 'pending';
  const submissionsActive = activeTab === 'my-submissions';

  return (
    <div className="reviews-tabs-shell">
      <nav className="reviews-tabs-nav" aria-label="Review list mode">
        <button
          type="button"
          onClick={() => onTabChange('pending')}
          className={`reviews-tab-btn ${pendingActive ? 'reviews-tab-btn--active' : ''}`}
        >
          <span
            className={`reviews-tab-icon ${pendingActive ? 'reviews-tab-icon--active' : ''}`}
            aria-hidden="true"
          >
            <Clock className="w-4 h-4" />
          </span>
          <span className="reviews-tab-copy">
            <span className="reviews-tab-title">Pending My Review</span>
            <span className="reviews-tab-subtitle">Assigned approvals</span>
          </span>
          {pendingCount > 0 ? (
            <span className="reviews-tab-count" aria-label={`${pendingCount} pending reviews`}>
              {pendingCount}
            </span>
          ) : null}
        </button>
        <button
          type="button"
          onClick={() => onTabChange('my-submissions')}
          className={`reviews-tab-btn ${submissionsActive ? 'reviews-tab-btn--active' : ''}`}
        >
          <span
            className={`reviews-tab-icon ${submissionsActive ? 'reviews-tab-icon--active' : ''}`}
            aria-hidden="true"
          >
            <Send className="w-4 h-4" />
          </span>
          <span className="reviews-tab-copy">
            <span className="reviews-tab-title">My Submissions</span>
            <span className="reviews-tab-subtitle">Requests I sent</span>
          </span>
        </button>
      </nav>
    </div>
  );
}
