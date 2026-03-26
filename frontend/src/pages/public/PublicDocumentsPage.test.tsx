import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PublicDocumentsPage from '@/pages/public/PublicDocumentsPage'

const mockGetDocuments = vi.fn()
const mockGetCategories = vi.fn()
const mockGetPlatformHistory = vi.fn()
const mockGetPlatformsOverview = vi.fn()

vi.mock('@/lib/publicApi', () => ({
  publicApi: {
    getDocuments: (...args: unknown[]) => mockGetDocuments(...args),
    getCategories: (...args: unknown[]) => mockGetCategories(...args),
    getPlatformHistory: (...args: unknown[]) => mockGetPlatformHistory(...args),
    getPlatformsOverview: (...args: unknown[]) => mockGetPlatformsOverview(...args),
  },
}))

vi.mock('@/components/SEO', () => ({
  SEO: () => null,
}))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function renderPage(initialUrl = '/docs') {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/docs" element={<PublicDocumentsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()

  mockGetDocuments.mockImplementation((params?: { category?: string; search?: string; page?: number }) => {
    if (params?.page === 2) {
      return Promise.resolve({
        items: [
          {
            id: 4,
            title: 'Second Page Doc',
            document_number: 'PUB-004',
            description: 'Paged result',
            category: 'Guides',
            platform: 'Beta',
            tags: 'page,two',
            visibility: 'public',
            created_at: '2026-04-01T00:00:00Z',
          },
        ],
        total: 14,
        page: 2,
        page_size: 12,
        total_pages: 2,
      })
    }

    if (params?.search === 'release') {
      return Promise.resolve({
        items: [
          {
            id: 3,
            title: 'Release Notes',
            document_number: 'PUB-003',
            description: 'Latest release summary',
            category: 'Release Notes',
            platform: 'Alpha',
            tags: 'release,updates',
            visibility: 'public',
            created_at: '2026-03-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 12,
        total_pages: 1,
      })
    }

    if (params?.category === 'API') {
      return Promise.resolve({
        items: [
          {
            id: 2,
            title: 'API Guide',
            document_number: 'PUB-002',
            description: 'Authentication and endpoints',
            category: 'API',
            platform: 'Alpha',
            tags: 'api,auth',
            visibility: 'public',
            created_at: '2026-02-10T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 12,
        total_pages: 1,
      })
    }

    return Promise.resolve({
      items: [
        {
          id: 1,
          title: 'Getting Started',
          document_number: 'PUB-001',
          description: 'First steps for new users',
          category: 'Guides',
          platform: 'Alpha',
          tags: 'intro,setup',
          visibility: 'public',
          created_at: '2026-01-15T00:00:00Z',
        },
      ],
      total: 14,
      page: 1,
      page_size: 12,
      total_pages: 2,
    })
  })

  mockGetCategories.mockResolvedValue({
    items: [
      { category: 'Guides', count: 8 },
      { category: 'API', count: 4 },
      { category: 'Guides / Setup', count: 3 },
    ],
    total: 3,
  })

  mockGetPlatformHistory.mockResolvedValue({
    items: [
      {
        platform: 'Alpha',
        categories: [
          {
            category: 'Guides',
            years: [
              {
                year: 2026,
                documents: [
                  {
                    id: 10,
                    title: 'Alpha Setup',
                    document_number: 'ALPHA-001',
                    release_branch: 'stable',
                    version_label: 'v2.0',
                    version_number: 2,
                    published_at: '2026-03-10T00:00:00Z',
                    updated_at: '2026-03-10T00:00:00Z',
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  })

  mockGetPlatformsOverview.mockResolvedValue({
    items: [{ id: 7, platform: 'Alpha', doc_count: 5, latest_release: null }],
  })
})

describe('PublicDocumentsPage', () => {
  it('renders public documents and platform highlights', async () => {
    renderPage()

    expect(screen.getByText('Documentation Library')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Getting Started')).toBeInTheDocument()
    })

    expect(screen.getByText('Platform highlights')).toBeInTheDocument()
    expect(screen.getByText('Alpha Setup')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /full platform history/i })).toHaveAttribute(
      'href',
      '/platforms',
    )
  })

  it('re-queries documents when a category filter is selected', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /API/ })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /API/ }))

    await waitFor(() => {
      expect(mockGetDocuments).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'API', page: 1, page_size: 12 }),
      )
    })

    expect(await screen.findByText('API Guide')).toBeInTheDocument()
  })

  it('submits search and paginates through results', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Getting Started')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText(/search public documents/i), {
      target: { value: 'release' },
    })
    fireEvent.submit(screen.getByLabelText(/search public documents/i).closest('form')!)

    await waitFor(() => {
      expect(mockGetDocuments).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'release', page: 1, page_size: 12 }),
      )
    })

    expect(await screen.findByText('PUB-003')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /clear all/i }))

    await waitFor(() => {
      expect(mockGetDocuments).toHaveBeenCalledWith(
        expect.objectContaining({ page: 1, page_size: 12 }),
      )
    })

    fireEvent.click(screen.getByRole('button', { name: /next page/i }))

    await waitFor(() => {
      expect(mockGetDocuments).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2, page_size: 12 }),
      )
    })

    expect(await screen.findByText('Second Page Doc')).toBeInTheDocument()
  })
})
