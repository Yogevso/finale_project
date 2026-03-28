import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DocumentsEmptyState } from './DocumentsEmptyState'

describe('DocumentsEmptyState', () => {
  it('shows reset guidance when filters hide all results', async () => {
    const user = userEvent.setup()
    const onClearFilters = vi.fn()

    render(
      <DocumentsEmptyState
        hasActiveFilters
        canCreate
        onCreate={vi.fn()}
        onUpload={vi.fn()}
        onClearFilters={onClearFilters}
      />,
    )

    expect(screen.getByText('No documents match your filters')).toBeInTheDocument()
    expect(screen.getByText('Search works on document title and document number.')).toBeInTheDocument()
    expect(screen.getByText('Filters stack together')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reset all filters' }))

    expect(onClearFilters).toHaveBeenCalled()
  })

  it('explains the create and upload paths when the library is empty', async () => {
    const user = userEvent.setup()
    const onCreate = vi.fn()
    const onUpload = vi.fn()

    render(
      <DocumentsEmptyState
        hasActiveFilters={false}
        canCreate
        onCreate={onCreate}
        onUpload={onUpload}
        onClearFilters={vi.fn()}
      />,
    )

    expect(screen.getByText('Start from a blank draft or upload an existing file. Visibility and company access can be configured after the draft exists.')).toBeInTheDocument()
    expect(screen.getByText('Best for net-new content, policies, and quick draft work.')).toBeInTheDocument()
    expect(screen.getByText('Import a DOCX or PPTX file and continue from existing source material.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Create document' }))
    await user.click(screen.getByRole('button', { name: 'Upload file' }))

    expect(onCreate).toHaveBeenCalled()
    expect(onUpload).toHaveBeenCalled()
  })
})
