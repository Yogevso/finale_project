import { describe, expect, it } from 'vitest'
import type { Attachment } from '@/types'
import {
  getPreferredEditorAttachment,
  getPreferredPreviewAttachment,
  resolveSelectedAttachment,
} from './attachmentSelection'

function buildAttachment(
  id: number,
  overrides: Partial<Attachment> = {},
): Attachment {
  return {
    id,
    document_id: 1,
    filename: `file-${id}.bin`,
    original_filename: `file-${id}.bin`,
    file_size: 100,
    mime_type: 'application/octet-stream',
    uploaded_by: 1,
    uploaded_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('attachmentSelection helpers', () => {
  it('prefers ready preview attachment over plain pdf and others', () => {
    const generic = buildAttachment(1)
    const pdf = buildAttachment(2, { mime_type: 'application/pdf' })
    const readyPreview = buildAttachment(3, {
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      preview_pdf_status: 'ready',
    })

    const selected = getPreferredPreviewAttachment([generic, pdf, readyPreview])

    expect(selected?.id).toBe(3)
  })

  it('falls back to pdf for preview selection when no ready artifact exists', () => {
    const generic = buildAttachment(1)
    const pdf = buildAttachment(2, { mime_type: 'application/pdf' })

    const selected = getPreferredPreviewAttachment([generic, pdf])

    expect(selected?.id).toBe(2)
  })

  it('refreshes selected attachment from updated list entry by id', () => {
    const oldSelection = buildAttachment(10, {
      filename: 'old-name.pdf',
      mime_type: 'application/pdf',
    })
    const refreshedSelection = buildAttachment(10, {
      filename: 'new-name.pdf',
      mime_type: 'application/pdf',
    })

    const resolved = resolveSelectedAttachment(
      [refreshedSelection],
      oldSelection,
      getPreferredPreviewAttachment,
    )

    expect(resolved).toBe(refreshedSelection)
    expect(resolved?.filename).toBe('new-name.pdf')
  })

  it('falls back to preferred attachment when selected id is removed', () => {
    const removed = buildAttachment(99, { mime_type: 'application/pdf' })
    const readyPreview = buildAttachment(3, {
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      preview_pdf_status: 'ready',
    })

    const resolved = resolveSelectedAttachment(
      [readyPreview],
      removed,
      getPreferredPreviewAttachment,
    )

    expect(resolved?.id).toBe(3)
  })

  it('prefers word attachments for editor selection, then pdf, then null', () => {
    const generic = buildAttachment(1)
    const pdf = buildAttachment(2, { mime_type: 'application/pdf' })
    const word = buildAttachment(3, {
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    expect(getPreferredEditorAttachment([generic, pdf, word])?.id).toBe(3)
    expect(getPreferredEditorAttachment([generic, pdf])?.id).toBe(2)
    expect(getPreferredEditorAttachment([generic])).toBeNull()
  })
})
