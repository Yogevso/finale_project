import { describe, expect, it, vi } from 'vitest'

import {
  buildDocumentsListQueryParams,
  createDocumentsUseCases,
  DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES,
  DOCUMENT_UPLOAD_MAX_SIZE_BYTES,
  validateDocumentUploadFile,
  type DocumentsUseCasesClient,
} from './documentsUseCases'

function createClientMocks(): DocumentsUseCasesClient {
  return {
    archiveDocument: vi.fn(),
    createDocument: vi.fn(),
    createVersion: vi.fn(),
    deleteDocument: vi.fn(),
    generateWordAttachment: vi.fn(),
    getAssignedCompanies: vi.fn(),
    getDeletedDocuments: vi.fn(),
    getDocument: vi.fn(),
    getDocumentCalendarExport: vi.fn(),
    getDocuments: vi.fn(),
    getVersion: vi.fn(),
    getVersions: vi.fn(),
    purgeDocument: vi.fn(),
    restoreDeletedDocument: vi.fn(),
    restoreDocument: vi.fn(),
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
      categoryFilter: '',
      companyIdFilter: null,
      dateFrom: '',
      dateTo: '',
    })

    expect(params).toEqual({
      page: 3,
      page_size: 25,
      search: undefined,
      status: undefined,
      visibility: undefined,
      category: undefined,
      company_id: undefined,
      date_from: undefined,
      date_to: undefined,
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
        platform: 'Core Platform',
        tags: 'release',
        content: '<p>Hello</p>',
      },
      { generateWord: true },
    )

    expect(result.id).toBe(11)
    expect(client.createDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Release Notes',
        status: 'draft',
        visibility: 'internal',
        platform: 'Core Platform',
      }),
    )
    expect(client.createVersion).toHaveBeenCalledWith(
      11,
      expect.objectContaining({ content: '<p>Hello</p>', changes_summary: 'Initial content' }),
    )
    expect(client.generateWordAttachment).toHaveBeenCalledWith(11, '<p>Hello</p>', 'Release Notes.docx')
  })

  it('creates a company-visible draft document with normalized company assignments', async () => {
    const client = createClientMocks()
    vi.mocked(client.createDocument).mockResolvedValue({ id: 33 } as never)

    const useCases = createDocumentsUseCases(client)
    await useCases.createDraftDocument(
      {
        title: 'Customer Notice',
        platform: 'Customer Platform',
        visibility: 'company',
        company_ids: [5, 5, 7],
        content: '',
      },
      { generateWord: false },
    )

    expect(client.createDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Customer Notice',
        visibility: 'company',
        company_ids: [5, 7],
      }),
    )
  })

  it('fails when generateWord is requested without content', async () => {
    const client = createClientMocks()
    vi.mocked(client.createDocument).mockResolvedValue({ id: 22 } as never)

    const useCases = createDocumentsUseCases(client)

    await expect(
      useCases.createDraftDocument(
        {
          title: 'Draft Without Body',
          platform: 'Core Platform',
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
    const onUploadProgress = vi.fn()

    await useCases.uploadDocument(file, {
      title: '  Policy  ',
      description: ' ',
      category: '  Security',
      platform: ' Core Platform ',
      releaseBranch: '',
      tags: 'tag-a,tag-b',
      status: 'approved',
    }, { onUploadProgress })

    expect(client.uploadDocument).toHaveBeenCalledWith(file, {
      title: 'Policy',
      description: undefined,
      category: 'Security',
      release_branch: undefined,
      tags: 'tag-a,tag-b',
      platform: 'Core Platform',
      status: 'approved',
      visibility: 'internal',
      company_ids: undefined,
      release_notes: undefined,
      content_file: undefined,
      pdf_conversion_target: undefined,
    }, { onUploadProgress })
  })

  it('forwards PDF conversion target metadata to the upload endpoint', async () => {
    const client = createClientMocks()
    vi.mocked(client.uploadDocument).mockResolvedValue({ id: 10 } as never)
    const useCases = createDocumentsUseCases(client)
    const file = { name: 'legacy.pdf', type: 'application/pdf', size: 10 } as File

    await useCases.uploadDocument(file, {
      title: 'Legacy PDF',
      description: '',
      category: '',
      platform: 'Core Platform',
      releaseBranch: '',
      tags: '',
      pdfConversionTarget: 'pptx',
    })

    expect(client.uploadDocument).toHaveBeenCalledWith(file, {
      title: 'Legacy PDF',
      description: undefined,
      category: undefined,
      release_branch: undefined,
      tags: undefined,
      platform: 'Core Platform',
      status: undefined,
      visibility: 'internal',
      company_ids: undefined,
      release_notes: undefined,
      content_file: undefined,
      pdf_conversion_target: 'pptx',
    }, undefined)
  })

  it('requires company selection when creating a company-visible document', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)

    await expect(
      useCases.createDraftDocument(
        {
          title: 'Company Guide',
          platform: 'Core Platform',
          visibility: 'company',
          company_ids: [],
        },
        { generateWord: false },
      ),
    ).rejects.toThrow('Select at least one company for company-visible documents.')

    expect(client.createDocument).not.toHaveBeenCalled()
  })

  it('rejects company assignments when creating a non-company-visible document', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)

    await expect(
      useCases.createDraftDocument(
        {
          title: 'Internal Policy',
          platform: 'Core Platform',
          visibility: 'internal',
          company_ids: [6],
        },
        { generateWord: false },
      ),
    ).rejects.toThrow('Company assignments are only allowed for company-visible documents.')

    expect(client.createDocument).not.toHaveBeenCalled()
  })

  it('requires company selection for company-visible uploads', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)
    const file = { name: 'policy.docx', type: '', size: 10 } as File

    await expect(
      useCases.uploadDocument(file, {
        title: 'Policy',
        description: '',
        category: '',
        platform: 'Core Platform',
        releaseBranch: '',
        tags: '',
        visibility: 'company',
        companyIds: [],
      }),
    ).rejects.toThrow('Select at least one company for company-visible documents.')

    expect(client.uploadDocument).not.toHaveBeenCalled()
  })

  it('rejects invalid company IDs for uploads before API call', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)
    const file = { name: 'policy.docx', type: '', size: 10 } as File

    await expect(
      useCases.uploadDocument(file, {
        title: 'Policy',
        description: '',
        category: '',
        platform: 'Core Platform',
        releaseBranch: '',
        tags: '',
        visibility: 'company',
        companyIds: [0],
      }),
    ).rejects.toThrow('Company assignments contain invalid company IDs.')

    expect(client.uploadDocument).not.toHaveBeenCalled()
  })

  it('requires a platform for uploads', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)
    const file = { name: 'policy.docx', type: '', size: 10 } as File

    await expect(
      useCases.uploadDocument(file, {
        title: 'Policy',
        description: '',
        category: '',
        releaseBranch: '',
        tags: '',
      }),
    ).rejects.toThrow('Platform is required.')

    expect(client.uploadDocument).not.toHaveBeenCalled()
  })

  it('requires a conversion target for PDF uploads before the API call', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)
    const file = { name: 'legacy.pdf', type: 'application/pdf', size: 10 } as File

    await expect(
      useCases.uploadDocument(file, {
        title: 'Legacy PDF',
        description: '',
        category: '',
        platform: 'Core Platform',
        releaseBranch: '',
        tags: '',
      }),
    ).rejects.toThrow('Choose how to convert this PDF before uploading.')

    expect(client.uploadDocument).not.toHaveBeenCalled()
  })

  it('validates upload files by type and size', () => {
    const unsupportedFile = { name: 'notes.txt', type: 'text/plain', size: 128 } as File
    const oversizedFile = {
      name: 'deck.pptx',
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      size: DOCUMENT_UPLOAD_MAX_SIZE_BYTES + 1,
    } as File
    const validFile = { name: 'guide.docx', type: '', size: 200 } as File

    expect(validateDocumentUploadFile(unsupportedFile)).toBe(
      'Only DOCX, PPTX, and PDF files are allowed',
    )
    expect(validateDocumentUploadFile(oversizedFile)).toBe('File size must be less than 50MB')
    expect(validateDocumentUploadFile(validFile)).toBeNull()
  })

  it('documents the current 50MB upload boundary', () => {
    expect(DOCUMENT_UPLOAD_MAX_SIZE_BYTES).toBe(50 * 1024 * 1024)
    expect(DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES).toContain('.pdf')
  })

  it('accepts PDF uploads in the client validation layer', () => {
    const pdfFile = {
      name: 'legacy.pdf',
      type: 'application/pdf',
      size: 2048,
    } as File

    expect(validateDocumentUploadFile(pdfFile)).toBeNull()
  })

  it('requires a platform for created drafts', async () => {
    const client = createClientMocks()
    const useCases = createDocumentsUseCases(client)

    await expect(
      useCases.createDraftDocument(
        {
          title: 'Platformless Draft',
          content: '<p>Body</p>',
        },
        { generateWord: false },
      ),
    ).rejects.toThrow('Platform is required.')

    expect(client.createDocument).not.toHaveBeenCalled()
  })

  it('builds an editable draft from an existing document', async () => {
    const client = createClientMocks()
    vi.mocked(client.getDocument).mockResolvedValue({
      id: 44,
      title: 'Source Guide',
      document_number: 'DOC-44',
      description: 'Copied description',
      visibility: 'company',
      category: 'Guides',
      tags: 'guide,copy',
      release_branch: 'R900',
      due_date: '2026-04-01',
      topic: 'firmware',
      platform: 'Meteor Lake',
      platform_id: 12,
    } as never)
    vi.mocked(client.getVersions).mockResolvedValue({
      items: [
        {
          id: 1,
          created_at: '2026-03-10T10:00:00Z',
          is_published: false,
          content: 'uploaded from file: source.docx',
        },
        {
          id: 2,
          created_at: '2026-03-11T10:00:00Z',
          published_at: '2026-03-12T10:00:00Z',
          is_published: true,
          content: '<h1>Source Guide</h1><p>Copied content</p>',
        },
      ],
      total: 2,
    } as never)
    vi.mocked(client.getAssignedCompanies).mockResolvedValue([
      { id: 7, name: 'Tenant Seven', slug: 'tenant-seven' },
    ] as never)

    const useCases = createDocumentsUseCases(client)
    const result = await useCases.loadDuplicateDocumentDraft(44)

    expect(result).toEqual(
      expect.objectContaining({
        title: 'Copy of Source Guide',
        description: 'Copied description',
        visibility: 'company',
        company_ids: [7],
        category: 'Guides',
        topic: 'firmware',
        platform: 'Meteor Lake',
        platform_id: 12,
        release_branch: 'R900',
        tags: 'guide,copy',
        due_date: '2026-04-01',
        content: '<h1>Source Guide</h1><p>Copied content</p>',
        parent_id: 44,
      }),
    )
  })
})
