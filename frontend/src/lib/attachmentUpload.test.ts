import { describe, expect, it } from 'vitest'

import {
  ATTACHMENT_INPUT_ACCEPT,
  ATTACHMENT_MAX_SIZE_BYTES,
  validateAttachmentFile,
} from './attachmentUpload'

describe('attachmentUpload', () => {
  it('includes pdf in the accepted upload extensions', () => {
    expect(ATTACHMENT_INPUT_ACCEPT).toContain('.pdf')
  })

  it('accepts pdf files so frontend validation matches the backend', () => {
    expect(
      validateAttachmentFile({
        name: 'manual.pdf',
        size: 1024,
        type: 'application/pdf',
      }),
    ).toBeNull()
  })

  it('rejects oversized files before upload starts', () => {
    expect(
      validateAttachmentFile({
        name: 'too-large.docx',
        size: ATTACHMENT_MAX_SIZE_BYTES + 1,
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      }),
    ).toBe('File too large. Max size: 50MB.')
  })

  it('documents the shared 50MB attachment boundary', () => {
    expect(ATTACHMENT_MAX_SIZE_BYTES).toBe(50 * 1024 * 1024)
  })
})
