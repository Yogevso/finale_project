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
  it('prefers DOCX and PPTX attachments for preview selection', () => {
    const generic = buildAttachment(1)
    const pptx = buildAttachment(2, {
      mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })
    const docx = buildAttachment(3, {
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    expect(getPreferredPreviewAttachment([generic, pptx, docx])?.id).toBe(2)
    expect(getPreferredPreviewAttachment([generic, docx])?.id).toBe(3)
  })

  it('refreshes selected attachment from updated list entry by id', () => {
    const oldSelection = buildAttachment(10, {
      filename: 'old-name.docx',
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const refreshedSelection = buildAttachment(10, {
      filename: 'new-name.docx',
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    const resolved = resolveSelectedAttachment(
      [refreshedSelection],
      oldSelection,
      getPreferredPreviewAttachment,
    )

    expect(resolved).toBe(refreshedSelection)
    expect(resolved?.filename).toBe('new-name.docx')
  })

  it('falls back to preferred attachment when selected id is removed', () => {
    const removed = buildAttachment(99, {
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const replacement = buildAttachment(3, {
      mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })

    const resolved = resolveSelectedAttachment(
      [replacement],
      removed,
      getPreferredPreviewAttachment,
    )

    expect(resolved?.id).toBe(3)
  })

  it('prefers DOCX attachments for editor selection', () => {
    const generic = buildAttachment(1)
    const docx = buildAttachment(2, {
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const pptx = buildAttachment(3, {
      mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })

    expect(getPreferredEditorAttachment([generic, pptx, docx])?.id).toBe(2)
    expect(getPreferredEditorAttachment([generic, pptx])).toBeNull()
  })
})
