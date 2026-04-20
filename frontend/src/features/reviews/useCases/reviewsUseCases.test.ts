import { describe, expect, it, vi } from 'vitest'

import {
  createReviewsUseCases,
  type ReviewsUseCasesClient,
} from './reviewsUseCases'

function createClientMocks(): ReviewsUseCasesClient {
  return {
    approveReview: vi.fn(),
    rejectReview: vi.fn(),
    cancelReview: vi.fn(),
  }
}

describe('reviews use cases', () => {
  it('delegates approve action to API client with comments payload', async () => {
    const client = createClientMocks()
    vi.mocked(client.approveReview).mockResolvedValue({ id: 1 } as never)

    const useCases = createReviewsUseCases(client)
    await useCases.approveReview(15, {
      comments: 'Ship it',
      generalComment: 'Ship it',
    })

    expect(client.approveReview).toHaveBeenCalledWith(15, {
      comments: 'Ship it',
      review_feedback: {
        general_comment: 'Ship it',
        section_comments: [],
      },
    })
  })

  it('delegates reject action with structured feedback payload', async () => {
    const client = createClientMocks()
    vi.mocked(client.rejectReview).mockResolvedValue({ id: 1 } as never)

    const useCases = createReviewsUseCases(client)
    await useCases.rejectReview(16, {
      comments: 'Needs changes',
      generalComment: 'Needs changes',
      sectionComments: [
        {
          title: 'Overview',
          comment: 'Clarify acceptance criteria.',
          anchor_id: 'h2-overview',
          severity: 'high',
        },
      ],
    })

    expect(client.rejectReview).toHaveBeenCalledWith(16, {
      comments: 'Needs changes',
      review_feedback: {
        general_comment: 'Needs changes',
        section_comments: [
          {
            title: 'Overview',
            comment: 'Clarify acceptance criteria.',
            anchor_id: 'h2-overview',
            severity: 'high',
            action_item_assignee: undefined,
          },
        ],
      },
    })
  })

  it('delegates cancel action to API client', async () => {
    const client = createClientMocks()
    vi.mocked(client.cancelReview).mockResolvedValue({ id: 1 } as never)

    const useCases = createReviewsUseCases(client)
    await useCases.cancelReview(17)

    expect(client.cancelReview).toHaveBeenCalledWith(17)
  })
})
