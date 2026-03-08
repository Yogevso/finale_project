import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CompanySelector from '@/components/CompanySelector'
import { api } from '@/lib/api'
import type { Company, CompanyListResponse } from '@/types'

const createdQueryClients: QueryClient[] = []
const getCompaniesMock = vi.spyOn(api, 'getCompanies')

function buildCompany(id: number, name: string): Company {
  return {
    id,
    name,
    slug: name.toLowerCase().replace(/\s+/g, '-'),
    company_type: 'customer',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    contact_email: null,
    company_logo: null,
    user_count: 0,
    owned_document_count: 0,
    assigned_document_count: 0,
    customer_visible_document_count: 0,
    document_count: 0,
  }
}

function buildCompanyListResponse(
  items: Company[],
  page = 1,
  pages = 1,
  perPage = 25,
): CompanyListResponse {
  return {
    items,
    total: items.length,
    page,
    pages,
    per_page: perPage,
  }
}

function createQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
  createdQueryClients.push(queryClient)
  return queryClient
}

function renderCompanySelector(
  props: Partial<ComponentProps<typeof CompanySelector>> = {},
) {
  const queryClient = createQueryClient()
  const defaultProps: ComponentProps<typeof CompanySelector> = {
    selectedIds: [],
    onChange: vi.fn(),
  }

  return render(
    <QueryClientProvider client={queryClient}>
      <CompanySelector {...defaultProps} {...props} />
    </QueryClientProvider>,
  )
}

describe('CompanySelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCompaniesMock.mockResolvedValue(buildCompanyListResponse([]))
  })

  afterEach(() => {
    vi.useRealTimers()
    cleanup()
    for (const queryClient of createdQueryClients) {
      queryClient.clear()
    }
    createdQueryClients.length = 0
  })

  it('renders loading state', async () => {
    getCompaniesMock.mockImplementation(
      () =>
        new Promise<CompanyListResponse>(() => {
          // Keep the query pending so loading content remains visible.
        }),
    )

    renderCompanySelector()
    fireEvent.click(screen.getByTestId('company-selector-trigger'))

    expect(await screen.findByTestId('company-selector-loading')).toBeInTheDocument()
    expect(screen.getByText('Loading companies...')).toBeInTheDocument()
  })

  it('emits selection changes when choosing a company', async () => {
    const onChange = vi.fn()
    getCompaniesMock.mockResolvedValue(
      buildCompanyListResponse([buildCompany(1, 'Acme Corp'), buildCompany(2, 'Beta Labs')]),
    )

    renderCompanySelector({ onChange })

    fireEvent.click(screen.getByTestId('company-selector-trigger'))
    fireEvent.click(await screen.findByTestId('company-selector-option-1'))

    expect(onChange).toHaveBeenCalledWith([1])
  })

  it('emits removal changes from selected chips', async () => {
    const onChange = vi.fn()
    const selectedCompany = buildCompany(7, 'Delta Team')

    renderCompanySelector({
      selectedIds: [7],
      selectedCompanyOptions: [selectedCompany],
      onChange,
    })

    expect(await screen.findByText('Delta Team')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('company-selector-remove-7'))
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('supports bulk clear for selected companies', () => {
    const onChange = vi.fn()
    renderCompanySelector({
      selectedIds: [1, 2],
      selectedCompanyOptions: [buildCompany(1, 'Acme Corp'), buildCompany(2, 'Beta Labs')],
      onChange,
    })

    fireEvent.click(screen.getByTestId('company-selector-clear-all'))
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('supports keyboard navigation and option selection', async () => {
    const onChange = vi.fn()
    getCompaniesMock.mockResolvedValue(
      buildCompanyListResponse([buildCompany(1, 'Acme Corp'), buildCompany(2, 'Beta Labs')]),
    )

    renderCompanySelector({ onChange })

    fireEvent.keyDown(screen.getByTestId('company-selector-trigger'), { key: 'Enter' })
    const searchInput = await screen.findByTestId('company-selector-search')
    await screen.findByTestId('company-selector-option-2')
    fireEvent.keyDown(searchInput, { key: 'End' })
    fireEvent.keyDown(searchInput, { key: 'Enter' })

    expect(onChange).toHaveBeenCalledWith([2])
  })

  it('closes the dropdown on Escape key', async () => {
    getCompaniesMock.mockResolvedValue(buildCompanyListResponse([buildCompany(1, 'Acme Corp')]))

    renderCompanySelector()

    fireEvent.keyDown(screen.getByTestId('company-selector-trigger'), { key: 'Enter' })
    const searchInput = await screen.findByTestId('company-selector-search')
    fireEvent.keyDown(searchInput, { key: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByTestId('company-selector-search')).not.toBeInTheDocument()
    })
  })

  it('respects disabled mode', async () => {
    renderCompanySelector({
      selectedIds: [3],
      selectedCompanyOptions: [buildCompany(3, 'Gamma Group')],
      onChange: vi.fn(),
      disabled: true,
    })

    expect(screen.getByTestId('company-selector-trigger')).toBeDisabled()
    expect(await screen.findByText('Gamma Group')).toBeInTheDocument()
    expect(screen.queryByTestId('company-selector-remove-3')).not.toBeInTheDocument()
    expect(screen.queryByTestId('company-selector-clear-all')).not.toBeInTheDocument()
  })

  it('supports API-backed pagination controls', async () => {
    getCompaniesMock.mockImplementation(async (params) => {
      if (params?.page === 2) {
        return buildCompanyListResponse([buildCompany(20, 'Page Two Company')], 2, 2, 1)
      }
      return buildCompanyListResponse([buildCompany(10, 'Page One Company')], 1, 2, 1)
    })

    renderCompanySelector({ perPage: 1 })

    fireEvent.click(screen.getByTestId('company-selector-trigger'))
    expect(await screen.findByTestId('company-selector-option-10')).toBeInTheDocument()
    expect(screen.getByTestId('company-selector-page-indicator')).toHaveTextContent('Page 1 of 2')

    fireEvent.click(screen.getByTestId('company-selector-next-page'))
    expect(await screen.findByTestId('company-selector-option-20')).toBeInTheDocument()
    expect(screen.getByTestId('company-selector-page-indicator')).toHaveTextContent('Page 2 of 2')
  })

  it('applies search input to the selector query params', async () => {
    const observedSearches: Array<string | undefined> = []
    getCompaniesMock.mockImplementation(async (params) => {
      observedSearches.push(params?.search)
      return buildCompanyListResponse([buildCompany(31, 'Acme Search Target')])
    })

    renderCompanySelector()

    fireEvent.click(screen.getByTestId('company-selector-trigger'))
    fireEvent.change(await screen.findByTestId('company-selector-search'), {
      target: { value: 'Acme' },
    })

    await waitFor(() => {
      expect(observedSearches).toContain('Acme')
    })
  })
})
