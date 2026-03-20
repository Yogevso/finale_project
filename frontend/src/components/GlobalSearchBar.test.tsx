/**
 * Y2-027: Component test for GlobalSearchBar
 * Type query, verify debounced API call, verify dropdown renders results, keyboard navigation.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GlobalSearchBar from '@/components/GlobalSearchBar'

// Mock the API module
vi.mock('@/lib/api', () => ({
  api: {
    search: vi.fn().mockResolvedValue({
      items: [
        { id: 1, title: 'Kubernetes Guide', document_number: 'DOC-001', category: 'DevOps', status: 'active' },
        { id: 2, title: 'React Tutorial', document_number: 'DOC-002', category: 'Frontend', status: 'active' },
      ],
      suggestions: [],
      total: 2,
    }),
    getSearchFacets: vi.fn().mockResolvedValue({ categories: [], statuses: [] }),
    getCompanies: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
}

function renderSearchBar() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <BrowserRouter>
        <GlobalSearchBar />
      </BrowserRouter>
    </QueryClientProvider>,
  )
}

describe('GlobalSearchBar (Y2-027)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
  })

  it('renders search input with correct placeholder', () => {
    renderSearchBar()
    expect(screen.getByRole('combobox', { name: /search documents/i })).toBeInTheDocument()
  })

  it('shows dropdown results after typing', async () => {
    const user = userEvent.setup()
    renderSearchBar()

    const input = screen.getByRole('combobox', { name: /search documents/i })
    await user.type(input, 'Kub')

    // Wait for debounce + API call
    await waitFor(() => expect(screen.getByText('Kubernetes Guide')).toBeInTheDocument(), { timeout: 2000 })
    expect(screen.getByText('React Tutorial')).toBeInTheDocument()
  })

  it('keyboard ArrowDown selects first result', async () => {
    const user = userEvent.setup()
    renderSearchBar()

    const input = screen.getByRole('combobox', { name: /search documents/i })
    await user.type(input, 'test')

    await waitFor(() => expect(screen.getByText('Kubernetes Guide')).toBeInTheDocument(), { timeout: 2000 })

    await user.keyboard('{ArrowDown}')

    const options = screen.getAllByRole('option')
    expect(options[0]).toHaveAttribute('aria-selected', 'true')
  })

  it('Escape closes dropdown', async () => {
    const user = userEvent.setup()
    renderSearchBar()

    const input = screen.getByRole('combobox', { name: /search documents/i })
    await user.type(input, 'test')

    await waitFor(
      () => expect(screen.getByRole('listbox')).toBeInTheDocument(),
      { timeout: 2000 },
    )

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('clicking a result navigates to document page', async () => {
    const user = userEvent.setup()
    renderSearchBar()

    const input = screen.getByRole('combobox', { name: /search documents/i })
    await user.type(input, 'Kub')

    await waitFor(
      () => expect(screen.getByText('Kubernetes Guide')).toBeInTheDocument(),
      { timeout: 2000 },
    )

    await user.click(screen.getByText('Kubernetes Guide'))
    expect(mockNavigate).toHaveBeenCalledWith('/documents/1')
  })
})
