import { fireEvent, render, screen } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { DocumentsFiltersToolbar } from './DocumentsFiltersToolbar'

describe('DocumentsFiltersToolbar', () => {
  it('opens the status menu with ArrowDown and focuses the first option', () => {
    render(
      <DocumentsFiltersToolbar
        isLoading={false}
        totalDocuments={12}
        search=""
        onSearchChange={vi.fn()}
        statusFilter=""
        onStatusFilterChange={vi.fn()}
        visibilityFilter=""
        onVisibilityFilterChange={vi.fn()}
        categoryFilter=""
        onCategoryFilterChange={vi.fn()}
        companyIdFilter={null}
        onCompanyIdFilterChange={vi.fn()}
        dateFrom=""
        onDateFromChange={vi.fn()}
        dateTo=""
        onDateToChange={vi.fn()}
        savedViews={[]}
        activeSavedViewId={null}
        onApplySavedView={vi.fn()}
        onSaveCurrentView={vi.fn()}
        onDeleteSavedView={vi.fn()}
        companies={[]}
        statusDetailsRef={createRef<HTMLDetailsElement>()}
        visibilityDetailsRef={createRef<HTMLDetailsElement>()}
      />,
    )

    const statusTrigger = screen.getByLabelText('Filter by status')
    statusTrigger.focus()
    fireEvent.keyDown(statusTrigger, { key: 'ArrowDown' })

    const allOptions = screen.getAllByRole('menuitemradio', { name: 'All' })
    expect(allOptions[0]).toHaveFocus()
  })
})
