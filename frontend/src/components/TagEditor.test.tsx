import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TagEditor from '@/components/TagEditor'

const getDocumentTagsMock = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getDocumentTags: (...args: unknown[]) => getDocumentTagsMock(...args),
  },
}))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function TagEditorHarness() {
  const [tags, setTags] = useState<string[]>([])

  return <TagEditor tags={tags} canEdit onSave={setTags} />
}

describe('TagEditor', () => {
  beforeEach(() => {
    getDocumentTagsMock.mockReset()
    getDocumentTagsMock.mockImplementation(async (query?: string) => {
      if (!query || query.trim() === '') {
        return []
      }
      if (query.toLowerCase().includes('sec')) {
        return ['Security', 'Security Ops']
      }
      return []
    })
  })

  it('shows autocomplete suggestions and adds a selected tag chip', async () => {
    const user = userEvent.setup()
    const queryClient = createQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <TagEditorHarness />
      </QueryClientProvider>,
    )

    await user.type(screen.getByPlaceholderText(/add a tag and press enter/i), 'sec')

    const suggestion = await screen.findByRole('button', { name: 'Security' })
    expect(screen.getByText('Suggestions')).toBeInTheDocument()

    await user.click(suggestion)

    await waitFor(() => {
      expect(screen.getByText('Security')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /remove security/i })).toBeInTheDocument()
  })
})
