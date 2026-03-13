import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { DocumentListResponse } from '@/types'
import { DocumentsTable } from './DocumentsTable'

vi.mock('@/components/BookmarkToggleButton', () => ({
  default: () => null,
}))

vi.mock('@/components/VisibilityBadge', () => ({
  default: ({ visibility }: { visibility: string }) => <span>{visibility}</span>,
}))

vi.mock('@/components/Skeleton', () => ({
  default: () => null,
}))

const tableData: DocumentListResponse = {
  items: [
    {
      id: 42,
      title: 'Document 42',
      document_number: 'DOC-42',
      description: null,
      status: 'draft',
      visibility: 'internal',
      category: 'Guide',
      tags: null,
      created_by: 1,
      created_at: '2026-03-13T10:00:00Z',
      updated_at: '2026-03-13T10:00:00Z',
      etag: 'etag-42',
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
  pages: 1,
}

describe('DocumentsTable', () => {
  it('shows a delete action for managers', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()

    render(
      <MemoryRouter>
        <DocumentsTable
          data={tableData}
          isLoading={false}
          isManager={true}
          page={1}
          visibilityOverrides={{}}
          selectedDocumentIds={[]}
          onToggleDocumentSelection={vi.fn()}
          onToggleAllVisibleDocuments={vi.fn()}
          onArchiveOrRestore={vi.fn()}
          onDelete={onDelete}
          onVisibilityChange={vi.fn()}
          onPageChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onDelete).toHaveBeenCalledWith(42, 'Document 42')
  })
})
