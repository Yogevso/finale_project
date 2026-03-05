import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useQuery } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CompanySelector from '@/components/CompanySelector'

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>(
    '@tanstack/react-query',
  )

  return {
    ...actual,
    useQuery: vi.fn(),
  }
})

const mockedUseQuery = vi.mocked(useQuery)

function buildCompany(id: number, name: string) {
  return {
    id,
    name,
    slug: name.toLowerCase().replace(/\s+/g, '-'),
    company_type: 'customer' as const,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    user_count: 0,
    owned_document_count: 0,
    assigned_document_count: 0,
    customer_visible_document_count: 0,
    document_count: 0,
  }
}

describe('CompanySelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders loading state', () => {
    mockedUseQuery.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[]} onChange={vi.fn()} />)
    fireEvent.click(screen.getByTestId('company-selector-trigger'))

    expect(screen.getByTestId('company-selector-loading')).toBeInTheDocument()
    expect(screen.getByText('Loading companies...')).toBeInTheDocument()
  })

  it('emits selection changes when choosing a company', () => {
    const onChange = vi.fn()
    mockedUseQuery.mockReturnValue({
      data: {
        items: [buildCompany(1, 'Acme Corp'), buildCompany(2, 'Beta Labs')],
        page: 1,
        pages: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[]} onChange={onChange} />)

    fireEvent.click(screen.getByTestId('company-selector-trigger'))
    fireEvent.click(screen.getByTestId('company-selector-option-1'))

    expect(onChange).toHaveBeenCalledWith([1])
  })

  it('emits removal changes from selected chips', () => {
    const onChange = vi.fn()
    mockedUseQuery.mockReturnValue({
      data: {
        items: [buildCompany(7, 'Delta Team')],
        page: 1,
        pages: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[7]} onChange={onChange} />)

    fireEvent.click(screen.getByTestId('company-selector-remove-7'))
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('supports bulk clear for selected companies', () => {
    const onChange = vi.fn()
    mockedUseQuery.mockReturnValue({
      data: {
        items: [buildCompany(1, 'Acme Corp'), buildCompany(2, 'Beta Labs')],
        page: 1,
        pages: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[1, 2]} onChange={onChange} />)

    fireEvent.click(screen.getByTestId('company-selector-clear-all'))
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('supports keyboard navigation and option selection', () => {
    const onChange = vi.fn()
    mockedUseQuery.mockReturnValue({
      data: {
        items: [buildCompany(1, 'Acme Corp'), buildCompany(2, 'Beta Labs')],
        page: 1,
        pages: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[]} onChange={onChange} />)

    fireEvent.keyDown(screen.getByTestId('company-selector-trigger'), { key: 'Enter' })
    const searchInput = screen.getByTestId('company-selector-search')
    fireEvent.keyDown(searchInput, { key: 'End' })
    fireEvent.keyDown(searchInput, { key: 'Enter' })

    expect(onChange).toHaveBeenCalledWith([2])
  })

  it('closes the dropdown on Escape key', () => {
    mockedUseQuery.mockReturnValue({
      data: {
        items: [buildCompany(1, 'Acme Corp')],
        page: 1,
        pages: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[]} onChange={vi.fn()} />)

    fireEvent.keyDown(screen.getByTestId('company-selector-trigger'), { key: 'Enter' })
    fireEvent.keyDown(screen.getByTestId('company-selector-search'), { key: 'Escape' })

    expect(screen.queryByTestId('company-selector-search')).not.toBeInTheDocument()
  })

  it('respects disabled mode', () => {
    mockedUseQuery.mockReturnValue({
      data: {
        items: [buildCompany(3, 'Gamma Group')],
        page: 1,
        pages: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never)

    render(<CompanySelector selectedIds={[3]} onChange={vi.fn()} disabled />)

    expect(screen.getByTestId('company-selector-trigger')).toBeDisabled()
    expect(screen.queryByTestId('company-selector-remove-3')).not.toBeInTheDocument()
    expect(screen.queryByTestId('company-selector-clear-all')).not.toBeInTheDocument()
  })

  it('supports API-backed pagination controls', () => {
    const pageOneResult = {
      data: {
        items: [buildCompany(10, 'Page One Company')],
        page: 1,
        pages: 2,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never
    const pageTwoResult = {
      data: {
        items: [buildCompany(20, 'Page Two Company')],
        page: 2,
        pages: 2,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as never

    mockedUseQuery.mockImplementation((queryOptions: any) => {
      const params = queryOptions.queryKey[2] as { page: number }
      if (params.page === 2) {
        return pageTwoResult
      }
      return pageOneResult
    })

    render(<CompanySelector selectedIds={[]} onChange={vi.fn()} perPage={1} />)

    fireEvent.click(screen.getByTestId('company-selector-trigger'))
    expect(screen.getByTestId('company-selector-option-10')).toBeInTheDocument()
    expect(screen.getByTestId('company-selector-page-indicator')).toHaveTextContent('Page 1 of 2')

    fireEvent.click(screen.getByTestId('company-selector-next-page'))
    expect(screen.getByTestId('company-selector-option-20')).toBeInTheDocument()
    expect(screen.getByTestId('company-selector-page-indicator')).toHaveTextContent('Page 2 of 2')
  })

  it('applies search input to the selector query params', async () => {
    vi.useFakeTimers()
    const observedParams: Array<{ search?: string }> = []
    mockedUseQuery.mockImplementation((queryOptions: any) => {
      observedParams.push((queryOptions.queryKey?.[2] ?? {}) as { search?: string })
      return {
        data: {
          items: [buildCompany(31, 'Acme Search Target')],
          page: 1,
          pages: 1,
        },
        isLoading: false,
        isError: false,
        isFetching: false,
      } as never
    })

    render(<CompanySelector selectedIds={[]} onChange={vi.fn()} />)

    fireEvent.click(screen.getByTestId('company-selector-trigger'))
    fireEvent.change(screen.getByTestId('company-selector-search'), {
      target: { value: 'Acme' },
    })
    act(() => {
      vi.advanceTimersByTime(300)
    })

    await waitFor(() => {
      expect(observedParams[observedParams.length - 1]?.search).toBe('Acme')
    })
    vi.useRealTimers()
  })
})
