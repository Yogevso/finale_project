import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { clearReviewProgress, markReviewStarted } from '../reviewProgress';
import { ReviewsTable } from './ReviewsTable';
import type { ReviewRequest } from '@/types';

function buildReview(overrides: Partial<ReviewRequest> = {}): ReviewRequest {
  return {
    id: 1,
    document_id: 42,
    version_id: 11,
    submitted_by: 7,
    reviewed_by: null,
    status: 'pending',
    message: 'Please review the latest draft.',
    review_comments: null,
    submitted_at: '2026-01-01T12:00:00Z',
    reviewed_at: null,
    created_at: '2026-01-01T12:00:00Z',
    document: {
      id: 42,
      title: 'Security Policy',
      document_number: 'DOC-42',
    } as ReviewRequest['document'],
    submitter: {
      id: 7,
      full_name: 'Taylor Reviewer',
    } as ReviewRequest['submitter'],
    ...overrides,
  };
}

describe('ReviewsTable', () => {
  beforeEach(() => {
    localStorage.clear();
    clearReviewProgress(1);
  });

  it('shows a new pending review without a separate view button', () => {
    render(
      <BrowserRouter>
        <ReviewsTable
          activeTab="pending"
          reviews={[buildReview()]}
          isLoading={false}
          total={1}
          cancelPending={false}
          onOpenReview={vi.fn()}
          onCancelReview={vi.fn()}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('New')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /review/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /view/i })).not.toBeInTheDocument();
  });

  it('shows in progress when the review was already started', () => {
    markReviewStarted(1, 0);

    render(
      <BrowserRouter>
        <ReviewsTable
          activeTab="pending"
          reviews={[buildReview()]}
          isLoading={false}
          total={1}
          cancelPending={false}
          onOpenReview={vi.fn()}
          onCancelReview={vi.fn()}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('renames rejected submissions to pending editor', () => {
    render(
      <BrowserRouter>
        <ReviewsTable
          activeTab="my-submissions"
          reviews={[
            buildReview({
              id: 2,
              status: 'rejected',
              reviewer: { id: 9, full_name: 'Morgan Manager' } as ReviewRequest['reviewer'],
            }),
          ]}
          isLoading={false}
          total={1}
          cancelPending={false}
          onOpenReview={vi.fn()}
          onCancelReview={vi.fn()}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('Pending editor')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /feedback/i })).toBeInTheDocument();
  });
});
