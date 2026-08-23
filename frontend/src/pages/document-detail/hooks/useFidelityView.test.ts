import { describe, expect, it } from 'vitest'
import type { Attachment } from '@/types'
import {
  getFidelityAttachment,
  supportsFidelityView,
} from '@/pages/document-detail/hooks/useFidelityView'

function createAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 1,
    document_id: 42,
    filename: 'document.docx',
    original_filename: 'document.docx',
    file_size: 1024,
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const PDF = createAttachment({
  id: 2,
  filename: 'spec.pdf',
  original_filename: 'spec.pdf',
  mime_type: 'application/pdf',
})

describe('supportsFidelityView', () => {
  it('accepts a PDF by mime type', () => {
    expect(supportsFidelityView(PDF)).toBe(true)
  })

  it('accepts a PDF whose mime type was not recorded', () => {
    expect(
      supportsFidelityView(createAttachment({ original_filename: 'spec.PDF', mime_type: '' })),
    ).toBe(true)
  })

  it('rejects the formats the reader renders itself', () => {
    expect(supportsFidelityView(createAttachment())).toBe(false)
    expect(supportsFidelityView(null)).toBe(false)
  })
})

describe('getFidelityAttachment', () => {
  it('finds the PDF even when the reader is showing a different attachment', () => {
    // Every document in the platform ships this pair, and the reader always selects the
    // DOCX: it is the only one of the two with a reader artifact. Reading the fidelity
    // attachment from that same selection left the original-layout view unreachable.
    const attachments = [createAttachment(), PDF]

    expect(getFidelityAttachment(attachments)?.id).toBe(PDF.id)
  })

  it('returns null when the document ships no PDF', () => {
    expect(getFidelityAttachment([createAttachment()])).toBeNull()
  })

  it('returns null for a document with no attachments', () => {
    expect(getFidelityAttachment([])).toBeNull()
  })
})
