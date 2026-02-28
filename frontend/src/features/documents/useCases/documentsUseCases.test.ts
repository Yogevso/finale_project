import { describe, expect, it, vi } from 'vitest'

import {
  buildDocumentsListQueryParams,
  createDocumentsUseCases,
  DOCUMENT_UPLOAD_MAX_SIZE_BYTES,
  validateDocumentUploadFile,
  type DocumentsUseCasesClient,
} from './documentsUseCases'

function createClientMocks(): DocumentsUseCasesClient {
  return {
    createDocument: vi.fn(),
    createVersion: vi.fn(),
    deleteDocument: vi.fn(),
    generateWordAttachment: vi.fn(),
    getDocuments: vi.fn(),
    updateDocument: vi.fn(),
    uploadDocument: vi.fn(),
  }
}

describe('documents use cases', () => {
  it('builds document list query params and omits empty filters', () => {
    const params = buildDocumentsListQueryParams({
      page: 3,
      pageSize: 25,
      search: '',
      statusFilter: '',
      visibilityFilter: '',
    })

    expect(params).toEqual({
      page: 3,
      page_size: 25,
      search: undefined,
      status: undefined,
      visibility: undefined,
    })
  })

  it('creates a draft document and initial version for non-empty content', async () => {
    const client = createClientMocks()
    vi.mocked(client.createDocument).mockResolvedValue({ id: 11 } as never)

    const useCases = createDocumentsUseCases(client)
    const result = await useCases.createDraftDocument(
      {
        title: 'Release Notes',
        description: 'Notes',
        category: 'Guides',
        tags: 'release',
        content: '<p>Hello</p>',
      },
      { generateWord: true },
    )

    expect(result.id).toBe(11)
    expect(client.createDocument).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Release Notes', status: 'draft', visibility: 'internal' }),
    )
    expect(client.createVersion).toHaveBeenCalledWith(
      11,
      expect.objectContaining({ content: '<p>Hello</p>', changes_summary: 'Initial content' }),
    )
    expect(client.generateWordAttachment).toHaveBeenCalledWith(11, '<p>Hello</p>', 'Release Notes.docx')
  })

  it('fails when generateWord is requested without content', async () => {
    const client = createClientMocks()
    vi.mocked(client.createDocument).mockResolvedValue({ id: 22 } as never)

    const useCases = createDocumentsUseCases(client)

    await expect(
      useCases.createDraftDocument(
        {
          title: 'Draft Without Body',
          content: '   ',
        },
        { generateWord: true },
      ),
    ).rejects.toThrow('Please add content before generating a Word file')

    expect(client.createVersion).not.toHaveBeenCalled()
    expect(client.generateWordAttachment).not.toHaveBeenCalled()
  })

  it('normalizes upload metadata before calling upload endpoint', async () => {
    const client = createClientMocks()
    vi.mocked(client.uploadDocument).mockResolvedValue({ id: 9 } as never)
    const useCases = createDocumentsUseCases(client)
    const file = { name: 'policy.docx', type: '', size: 10 } as File

    await useCases.uploadDocument(file, {
      title: '  Policy  ',
      description: ' ',
      category: '  Security',
      releaseBranch: '',
      tags: 'tag-a,tag-b',
    })

    expect(client.uploadDocument).toHaveBeenCalledWith(file, {
      title: 'Policy',
      description: undefined,
      category: 'Security',
      release_branch: undefined,
      tags: 'tag-a,tag-b',
    })
  })

  it('validates upload files by type and size', () => {
    const unsupportedFile = { name: 'notes.txt', type: 'text/plain', size: 128 } as File
    const oversizedFile = {
      name: 'archive.pdf',
      type: 'application/pdf',
      size: DOCUMENT_UPLOAD_MAX_SIZE_BYTES + 1,
    } as File
    const validFile = { name: 'guide.docx', type: '', size: 200 } as File

    expect(validateDocumentUploadFile(unsupportedFile)).toBe('Only PDF and Word documents are allowed')
    expect(validateDocumentUploadFile(oversizedFile)).toBe('File size must be less than 10MB')
    expect(validateDocumentUploadFile(validFile)).toBeNull()
  })
})

