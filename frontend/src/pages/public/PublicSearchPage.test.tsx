import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PublicSearchPage from '@/pages/public/PublicSearchPage'

const getCategoriesMock = vi.fn()
const searchMock = vi.fn()

vi.mock('@/lib/publicApi', () => ({
  publicApi: {
    getCategories: (...args: unknown[]) => getCategoriesMock(...args),
    search: (...args: unknown[]) => searchMock(...args),
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

function renderPage(initialUrl: string) {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/search" element={<PublicSearchPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PublicSearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCategoriesMock.mockResolvedValue({ items: [], total: 0 })
  })

  it('does not crash on regex-special queries and highlights literal matches', async () => {
    searchMock.mockResolvedValue({
      query: '(a',
      items: [
        {
          id: 1,
          document_number: 'DOC-REGEX-001',
          title: 'Guide (a) Pattern',
          snippet: 'This result includes (a) in text.',
          score: 1,
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    })

    renderPage('/search?q=%28a')

    expect(await screen.findByText(/Found 1 results for/i)).toBeInTheDocument()
    expect(screen.getByText('DOC-REGEX-001')).toBeInTheDocument()
    expect(searchMock).toHaveBeenCalled()
    expect(document.querySelectorAll('mark').length).toBeGreaterThan(0)
  })

  it('keeps normal alphanumeric highlighting behavior', async () => {
    searchMock.mockResolvedValue({
      query: 'guide',
      items: [
        {
          id: 2,
          document_number: 'DOC-TEXT-001',
          title: 'Guide Overview',
          snippet: 'Guide section summary.',
          score: 1,
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    })

    renderPage('/search?q=guide')

    expect(await screen.findByText(/Found 1 results for/i)).toBeInTheDocument()
    const highlightedMarks = Array.from(document.querySelectorAll('mark')).map((node) =>
      node.textContent?.toLowerCase(),
    )
    expect(highlightedMarks).toContain('guide')
  })
})
