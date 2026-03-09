import { expect, type Page } from '@playwright/test'
import { type Credentials, getApiAuthHeaders } from './auth'

type CreateDocumentInput = {
  title: string
  description?: string
  category?: string
  status?: 'draft' | 'pending_review' | 'approved' | 'active' | 'archived'
  visibility?: 'internal' | 'public' | 'company'
}

type CreateVersionInput = {
  content: string
  changes_summary: string
  bump_type?: 'patch' | 'minor' | 'major'
}

type DocumentRecord = {
  id: number
  title: string
  category: string | null
}

type DocumentListResponse = {
  items: DocumentRecord[]
}

export async function createDocumentViaApi(
  page: Page,
  credentials: Credentials,
  input: CreateDocumentInput,
) {
  const headers = await getApiAuthHeaders(page, credentials)
  const response = await page.request.post('/api/v1/documents', {
    headers,
    data: {
      title: input.title,
      description: input.description ?? 'Created by Playwright',
      category: input.category ?? 'Operations',
      status: input.status ?? 'draft',
      visibility: input.visibility ?? 'internal',
    },
  })

  expect(response.ok(), `Expected document creation to succeed for ${input.title}`).toBeTruthy()
  return (await response.json()) as {
    id: number
    title: string
    category: string | null
  }
}

export async function createVersionViaApi(
  page: Page,
  credentials: Credentials,
  documentId: number,
  input: CreateVersionInput,
) {
  const headers = await getApiAuthHeaders(page, credentials)
  const response = await page.request.post(`/api/v1/documents/${documentId}/versions`, {
    headers,
    data: {
      content: input.content,
      changes_summary: input.changes_summary,
      bump_type: input.bump_type ?? 'patch',
    },
  })

  expect(response.ok(), `Expected version creation to succeed for document ${documentId}`).toBeTruthy()
  return (await response.json()) as {
    id: number
    version_number: number
    content: string | null
  }
}

export async function searchDocumentsViaApi(
  page: Page,
  credentials: Credentials,
  search: string,
) {
  const headers = await getApiAuthHeaders(page, credentials)
  const response = await page.request.get('/api/v1/documents', {
    headers,
    params: {
      search,
      page: '1',
      page_size: '20',
    },
  })

  expect(response.ok(), `Expected document search to succeed for ${search}`).toBeTruthy()
  return (await response.json()) as DocumentListResponse
}
