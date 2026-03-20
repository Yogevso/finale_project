import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import ReviewDialog from './ReviewDialog'
import type { ReviewRequest } from '@/types'

function buildReview(overrides: Partial<ReviewRequest> = {}): ReviewRequest {
  return {
    id: 1,
    document_id: 42,
    version_id: null,
    submitted_by: 7,
    reviewed_by: null,
    status: 'pending',
    message: 'Please take a look at the latest draft.',
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
  }
}

describe('ReviewDialog', () => {
  it('shows inline rejection guidance instead of using a browser alert', async () => {
    const user = userEvent.setup()

    render(
      <BrowserRouter>
        <ReviewDialog
          review={buildReview()}
          onClose={vi.fn()}
          onApprove={vi.fn()}
          onReject={vi.fn()}
          isLoading={false}
        />
      </BrowserRouter>,
    )

    expect(screen.getByRole('dialog', { name: /review document/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /reject/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Rejection comments are required before you can confirm.',
    )
    expect(screen.getByRole('textbox', { name: /review comments/i })).toHaveAttribute(
      'aria-invalid',
      'true',
    )
  })
})
