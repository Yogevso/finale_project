import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'
import { useAttachmentDownload } from './useAttachmentDownload'

vi.mock('@/lib/api', () => ({
  api: {
    getAttachmentBlob: vi.fn(),
  },
}))

const mockedApi = vi.mocked(api, true)

function buildAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 1,
    document_id: 42,
    filename: 'file.docx',
    original_filename: 'file.docx',
    file_size: 128,
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('useAttachmentDownload', () => {
  const createObjectURLMock = vi.fn(() => 'blob:test')
  const revokeObjectURLMock = vi.fn()
  const anchorClickMock = vi.fn()
  const appendChildMock = vi.fn()
  const removeMock = vi.fn()
  const originalCreateElement = document.createElement.bind(document)
  const originalAppendChild = document.body.appendChild.bind(document.body)

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    document.body.innerHTML = ''
    mockedApi.getAttachmentBlob.mockResolvedValue(new Blob(['test']))

    vi.stubGlobal('URL', {
      createObjectURL: createObjectURLMock,
      revokeObjectURL: revokeObjectURLMock,
    })

    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const element = originalCreateElement(tagName)

      if (tagName.toLowerCase() === 'a') {
        const anchor = element as HTMLAnchorElement
        const originalRemove = anchor.remove.bind(anchor)
        anchor.click = anchorClickMock
        anchor.remove = () => {
          removeMock()
          originalRemove()
        }
        return anchor
      }

      return element
    })
    vi.spyOn(document.body, 'appendChild').mockImplementation((node: Node) => {
      appendChildMock(node)
      return originalAppendChild(node)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('downloads an attachment and cleans up the object url', async () => {
    const attachment = buildAttachment()
    const { result } = renderHook(() => useAttachmentDownload(42))

    await act(async () => {
      await result.current.downloadAttachment(attachment)
    })

    expect(mockedApi.getAttachmentBlob).toHaveBeenCalledWith(42, attachment.id)
    expect(createObjectURLMock).toHaveBeenCalledTimes(1)
    expect(
      appendChildMock.mock.calls.filter(([node]) => node instanceof HTMLAnchorElement),
    ).toHaveLength(1)
    expect(anchorClickMock).toHaveBeenCalledTimes(1)
    expect(removeMock).toHaveBeenCalledTimes(1)
    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:test')
    expect(result.current.downloadingAttachmentId).toBeNull()
  })

  it('tracks the active download while it is in flight', async () => {
    let resolveBlob: (blob: Blob) => void = () => undefined
    mockedApi.getAttachmentBlob.mockImplementation(
      () =>
        new Promise<Blob>((resolve) => {
          resolveBlob = resolve
        }),
    )

    const attachment = buildAttachment()
    const { result } = renderHook(() => useAttachmentDownload(42))

    let pendingDownload!: Promise<void>
    act(() => {
      pendingDownload = result.current.downloadAttachment(attachment)
    })

    await waitFor(() => {
      expect(result.current.downloadingAttachmentId).toBe(attachment.id)
    })

    await act(async () => {
      resolveBlob(new Blob(['done']))
      await pendingDownload
    })

    await waitFor(() => {
      expect(result.current.downloadingAttachmentId).toBeNull()
    })
  })
})
