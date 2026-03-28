import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { NO_DOCUMENT_DESCRIPTION_LABEL, UNTITLED_DOCUMENT_LABEL } from '@/lib/documentDisplay'
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
  total_pages: 1,
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
          isAdmin={true}
          isManager={true}
          showDeleted={false}
          page={1}
          visibilityOverrides={{}}
          selectedDocumentIds={[]}
          onToggleDocumentSelection={vi.fn()}
          onToggleAllVisibleDocuments={vi.fn()}
          onArchiveOrRestore={vi.fn()}
          onDelete={onDelete}
          onRestoreDeleted={vi.fn()}
          onPurgeDeleted={vi.fn()}
          onVisibilityChange={vi.fn()}
          onPageChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('table', { name: /documents list/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Delete Document 42' }))

    expect(onDelete).toHaveBeenCalledWith(42, 'Document 42')
  })

  it('shows restore and purge actions in the recovery window', async () => {
    const user = userEvent.setup()
    const onRestoreDeleted = vi.fn()
    const onPurgeDeleted = vi.fn()

    render(
      <MemoryRouter>
        <DocumentsTable
          data={{
            ...tableData,
            items: [
              {
                ...tableData.items[0],
                deleted_at: '2026-03-28T10:00:00Z',
                purge_at: '2026-04-27T10:00:00Z',
              },
            ],
          }}
          isLoading={false}
          isAdmin={true}
          isManager={true}
          showDeleted={true}
          page={1}
          visibilityOverrides={{}}
          selectedDocumentIds={[]}
          onToggleDocumentSelection={vi.fn()}
          onToggleAllVisibleDocuments={vi.fn()}
          onArchiveOrRestore={vi.fn()}
          onDelete={vi.fn()}
          onRestoreDeleted={onRestoreDeleted}
          onPurgeDeleted={onPurgeDeleted}
          onVisibilityChange={vi.fn()}
          onPageChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Restore Document 42' }))
    await user.click(screen.getByRole('button', { name: 'Permanently delete Document 42' }))

    expect(onRestoreDeleted).toHaveBeenCalledWith(42, 'Document 42')
    expect(onPurgeDeleted).toHaveBeenCalledWith(42, 'Document 42')
  })

  it('renders normalized titles and description previews for edge-case values', () => {
    render(
      <MemoryRouter>
        <DocumentsTable
          data={{
            ...tableData,
            items: [
              {
                ...tableData.items[0],
                id: 77,
                title:
                  '  Extremely long document title for customer rollout planning with an-unbroken-token-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789  ',
                document_number: 'DOC-77',
                description:
                  '  Line one of the description.\nLine two with more detail for reviewers and customers.  ',
              },
              {
                ...tableData.items[0],
                id: 78,
                title: '   ',
                document_number: 'DOC-78',
                description: '\n   \t',
              },
            ],
            total: 2,
          }}
          isLoading={false}
          isAdmin={true}
          isManager={true}
          showDeleted={false}
          page={1}
          visibilityOverrides={{}}
          selectedDocumentIds={[]}
          onToggleDocumentSelection={vi.fn()}
          onToggleAllVisibleDocuments={vi.fn()}
          onArchiveOrRestore={vi.fn()}
          onDelete={vi.fn()}
          onRestoreDeleted={vi.fn()}
          onPurgeDeleted={vi.fn()}
          onVisibilityChange={vi.fn()}
          onPageChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(
        'Extremely long document title for customer rollout planning with an-unbroken-token-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText((_, element) =>
        element?.tagName.toLowerCase() === 'p' &&
        element.textContent === 'Line one of the description.\nLine two with more detail for reviewers and customers.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(UNTITLED_DOCUMENT_LABEL)).toBeInTheDocument()
    expect(screen.getByText(NO_DOCUMENT_DESCRIPTION_LABEL)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Delete ${UNTITLED_DOCUMENT_LABEL}` })).toBeInTheDocument()
  })

  it('deep-links Manage companies to the detail assignment section', () => {
    render(
      <MemoryRouter>
        <DocumentsTable
          data={{
            ...tableData,
            items: [
              {
                ...tableData.items[0],
                visibility: 'company',
              },
            ],
          }}
          isLoading={false}
          isAdmin={true}
          isManager={true}
          showDeleted={false}
          page={1}
          visibilityOverrides={{ 42: 'company' }}
          selectedDocumentIds={[]}
          onToggleDocumentSelection={vi.fn()}
          onToggleAllVisibleDocuments={vi.fn()}
          onArchiveOrRestore={vi.fn()}
          onDelete={vi.fn()}
          onRestoreDeleted={vi.fn()}
          onPurgeDeleted={vi.fn()}
          onVisibilityChange={vi.fn()}
          onPageChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Manage companies' })).toHaveAttribute(
      'href',
      '/documents/42?tab=details&manage_companies=1#company-assignments',
    )
  })
})
