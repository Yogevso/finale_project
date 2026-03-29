import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { DocumentsFiltersToolbar } from './DocumentsFiltersToolbar'

function renderToolbar(overrides: Partial<Parameters<typeof DocumentsFiltersToolbar>[0]> = {}) {
  const props = {
    isLoading: false,
    totalDocuments: 12,
    isAdmin: true,
    showDeleted: false,
    onShowDeletedChange: vi.fn(),
    search: '',
    onSearchChange: vi.fn(),
    statusFilter: '',
    onStatusFilterChange: vi.fn(),
    visibilityFilter: '',
    onVisibilityFilterChange: vi.fn(),
    categoryFilter: '',
    onCategoryFilterChange: vi.fn(),
    companyIdFilter: null,
    onCompanyIdFilterChange: vi.fn(),
    dateFrom: '',
    onDateFromChange: vi.fn(),
    dateTo: '',
    onDateToChange: vi.fn(),
    onResetFilters: vi.fn(),
    savedViews: [],
    activeSavedViewId: null,
    onApplySavedView: vi.fn(),
    onSaveCurrentView: vi.fn(),
    onDeleteSavedView: vi.fn(),
    companies: [],
    categorySuggestions: [],
    searchSuggestions: [],
    statusDetailsRef: createRef<HTMLDetailsElement>(),
    visibilityDetailsRef: createRef<HTMLDetailsElement>(),
    ...overrides,
  } satisfies Parameters<typeof DocumentsFiltersToolbar>[0]

  render(<DocumentsFiltersToolbar {...props} />)
  return props
}

describe('DocumentsFiltersToolbar', () => {
  it('opens the status menu with ArrowDown and focuses the first option', () => {
    renderToolbar()

    expect(screen.getByTestId('documents-filters-toolbar')).toHaveClass('admin-sticky-toolbar')

    const statusTrigger = screen.getByLabelText('Filter by status')
    statusTrigger.focus()
    fireEvent.keyDown(statusTrigger, { key: 'ArrowDown' })

    const allOptions = screen.getAllByRole('menuitemradio', { name: 'All' })
    expect(allOptions[0]).toHaveFocus()
  })

  it('renders suggestions, active filter chips, and clear actions', async () => {
    const user = userEvent.setup()
    const onSearchChange = vi.fn()
    const onCategoryFilterChange = vi.fn()
    const onResetFilters = vi.fn()

    renderToolbar({
      totalDocuments: 3,
      search: 'Safety',
      onSearchChange,
      statusFilter: 'draft',
      categoryFilter: 'Policy',
      onCategoryFilterChange,
      companyIdFilter: 7,
      dateFrom: '2026-03-01',
      onResetFilters,
      companies: [{ id: 7, name: 'Acme Co' } as never],
      categorySuggestions: ['Guide', 'Policy'],
      searchSuggestions: ['DOC-42', 'Safety Manual'],
    })

    expect(screen.getByText('3 matching')).toBeInTheDocument()
    expect(screen.getByText('5 active filters')).toBeInTheDocument()
    expect(
      document.querySelector('datalist#documents-search-suggestions option[value="Safety Manual"]'),
    ).not.toBeNull()
    expect(
      document.querySelector('datalist#documents-category-suggestions option[value="Policy"]'),
    ).not.toBeNull()
    expect(screen.getByRole('button', { name: 'Remove Category: Policy' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear all filters' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Remove Category: Policy' }))
    await user.click(screen.getByRole('button', { name: 'Clear all filters' }))
    await user.click(screen.getByRole('button', { name: 'Clear search' }))

    expect(onCategoryFilterChange).toHaveBeenCalledWith('')
    expect(onResetFilters).toHaveBeenCalled()
    expect(onSearchChange).toHaveBeenCalledWith('')
  })

  it('warns when the created date range is inverted', () => {
    renderToolbar({
      dateFrom: '2026-03-28',
      dateTo: '2026-03-01',
    })

    expect(
      screen.getByText('Created after must be on or before created before.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Created after')).toHaveAttribute('max', '2026-03-01')
    expect(screen.getByLabelText('Created before')).toHaveAttribute('min', '2026-03-28')
  })
})
