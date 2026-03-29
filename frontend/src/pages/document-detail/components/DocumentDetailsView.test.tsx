import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { AudienceAccessPreview, Company, Document } from '@/types'
import { DocumentDetailsView } from './DocumentDetailsView'

const TEST_TIMESTAMP = '2026-03-28T12:00:00Z'

const baseDocument: Document = {
  id: 42,
  title: 'Customer Release Notes',
  document_number: 'DOC-42',
  description: 'Audience guidance test document',
  status: 'draft',
  visibility: 'company',
  category: 'Releases',
  tags: null,
  created_by: 7,
  created_at: TEST_TIMESTAMP,
  updated_at: TEST_TIMESTAMP,
}

const assignedCompany: Company = {
  id: 9,
  name: 'Customer One',
  slug: 'customer-one',
  is_active: true,
  company_type: 'customer',
  created_at: TEST_TIMESTAMP,
  updated_at: TEST_TIMESTAMP,
  user_count: 3,
  owned_document_count: 0,
  assigned_document_count: 1,
  customer_visible_document_count: 0,
  document_count: 1,
}

const audiencePreview: AudienceAccessPreview = {
  visibility: 'company',
  is_public: false,
  includes_internal_users: true,
  target_companies: [
    {
      id: assignedCompany.id,
      name: assignedCompany.name,
      slug: assignedCompany.slug,
    },
  ],
  access_summary:
    '1 assigned company is staged, but customers will not see this document until it is marked Published and a version has been published.',
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

describe('DocumentDetailsView', () => {
  it('shows publish guidance for company-visible drafts instead of claiming access is already live', () => {
    const queryClient = createQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <DocumentDetailsView
          document={baseDocument}
          isEditor={false}
          canAssignCompanies={true}
          showCompanySelector={false}
          onToggleCompanySelector={vi.fn()}
          assignedCompanies={[assignedCompany]}
          assignmentDraftIds={[assignedCompany.id]}
          hasUnsavedAssignmentChanges={false}
          audienceAccessPreview={audiencePreview}
          onAssignmentDraftChange={vi.fn()}
          onSaveAssignmentDraft={vi.fn()}
          onDiscardAssignmentDraft={vi.fn()}
          isAssigningCompanies={false}
          onRemoveCompany={vi.fn()}
          isRemovingCompany={false}
          onSaveTags={vi.fn()}
          isSavingTags={false}
          reviewHistoryItems={[]}
        />
      </QueryClientProvider>,
    )

    expect(
      screen.getAllByText(
        '1 assigned company is staged, but customers will not see this document until it is marked Published and a version has been published.',
      ),
    ).toHaveLength(2)
    expect(
      screen.queryByText('Assigned companies currently have audience access.'),
    ).not.toBeInTheDocument()
  })
})
