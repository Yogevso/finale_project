import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { Toaster } from 'sonner'

import { extractApiErrorMessage, useToast } from './toast'

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function MutationToastHarness() {
  const toast = useToast()

  const successMutation = useMutation({
    mutationFn: async () => 'ok',
    onSuccess: () => {
      toast.success('Mutation succeeded', 'Saved successfully')
    },
  })

  const errorMutation = useMutation({
    mutationFn: async () => {
      throw new Error('Server exploded')
    },
    onError: (error: unknown) => {
      toast.error('Mutation failed', extractApiErrorMessage(error, 'Unknown error'))
    },
  })

  return (
    <>
      <button type="button" onClick={() => successMutation.mutate()}>
        Trigger success
      </button>
      <button type="button" onClick={() => errorMutation.mutate()}>
        Trigger error
      </button>
      <Toaster position="top-right" richColors />
    </>
  )
}

describe('global toast system', () => {
  it('renders success and error toasts when mutations settle', async () => {
    const user = userEvent.setup()
    const queryClient = createQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <MutationToastHarness />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: /trigger success/i }))
    await waitFor(() => {
      expect(screen.getByText('Mutation succeeded')).toBeInTheDocument()
      expect(screen.getByText('Saved successfully')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /trigger error/i }))
    await waitFor(() => {
      expect(screen.getByText('Mutation failed')).toBeInTheDocument()
      expect(screen.getByText('Server exploded')).toBeInTheDocument()
    })
  })

  it('does not move focus away from the triggering control when a toast appears', async () => {
    const user = userEvent.setup()
    const queryClient = createQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <MutationToastHarness />
      </QueryClientProvider>,
    )

    const trigger = screen.getByRole('button', { name: /trigger success/i })
    trigger.focus()

    expect(trigger).toHaveFocus()

    await user.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Mutation succeeded')).toBeInTheDocument()
    })

    expect(trigger).toHaveFocus()
  })
})
