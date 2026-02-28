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
    await useCases.approveReview(15, 'Ship it')

    expect(client.approveReview).toHaveBeenCalledWith(15, { comments: 'Ship it' })
  })

  it('delegates reject action to API client', async () => {
    const client = createClientMocks()
    vi.mocked(client.rejectReview).mockResolvedValue({ id: 1 } as never)

    const useCases = createReviewsUseCases(client)
    await useCases.rejectReview(16, 'Needs changes')

    expect(client.rejectReview).toHaveBeenCalledWith(16, { comments: 'Needs changes' })
  })

  it('delegates cancel action to API client', async () => {
    const client = createClientMocks()
    vi.mocked(client.cancelReview).mockResolvedValue({ id: 1 } as never)

    const useCases = createReviewsUseCases(client)
    await useCases.cancelReview(17)

    expect(client.cancelReview).toHaveBeenCalledWith(17)
  })
})

