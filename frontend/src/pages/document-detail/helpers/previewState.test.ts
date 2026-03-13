import { describe, expect, it } from 'vitest'
import type { Attachment } from '@/types'
import {
  decidePreviewState,
  getPreviewableAttachments,
  isPreviewableAttachment,
  normalizeReaderPreviewStatus,
} from './previewState'

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

describe('previewState helpers', () => {
  it('detects previewable attachments by mime type', () => {
    expect(isPreviewableAttachment(buildAttachment())).toBe(true)
    expect(
      isPreviewableAttachment(buildAttachment({ mime_type: 'application/octet-stream' })),
    ).toBe(false)
  })

  it('filters previewable attachments', () => {
    const attachments = [
      buildAttachment({ id: 1 }),
      buildAttachment({ id: 2, mime_type: 'application/octet-stream' }),
      buildAttachment({
        id: 3,
        mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      }),
    ]

    expect(getPreviewableAttachments(attachments).map((attachment) => attachment.id)).toEqual([1, 3])
  })

  it('normalizes reader statuses', () => {
    expect(normalizeReaderPreviewStatus('processing')).toBe('pending')
    expect(normalizeReaderPreviewStatus('pending')).toBe('pending')
    expect(normalizeReaderPreviewStatus('ready')).toBe('ready')
    expect(normalizeReaderPreviewStatus('failed')).toBe('failed')
    expect(normalizeReaderPreviewStatus(null)).toBe('idle')
  })

  it('returns READY when inline content exists', () => {
    expect(
      decidePreviewState({
        attachments: [],
        inlineContent: '<p>ready</p>',
        readerStatus: 'idle',
      }),
    ).toBe('READY')
  })

  it('returns NO_CONTENT when there is no attachment and no inline content', () => {
    expect(
      decidePreviewState({
        attachments: [],
        inlineContent: null,
        readerStatus: 'idle',
      }),
    ).toBe('NO_CONTENT')
  })

  it('returns DOWNLOAD_ONLY when attachments exist but none are previewable', () => {
    expect(
      decidePreviewState({
        attachments: [buildAttachment({ mime_type: 'application/octet-stream' })],
        inlineContent: null,
        readerStatus: 'idle',
      }),
    ).toBe('DOWNLOAD_ONLY')
  })

  it('returns LOADING when previewable attachments exist and reader is pending', () => {
    expect(
      decidePreviewState({
        attachments: [buildAttachment()],
        inlineContent: null,
        readerStatus: 'pending',
      }),
    ).toBe('LOADING')
  })

  it('returns LOADING when previewable attachments exist and reader has not started yet', () => {
    expect(
      decidePreviewState({
        attachments: [buildAttachment()],
        inlineContent: null,
        readerStatus: 'idle',
      }),
    ).toBe('LOADING')
  })

  it('returns ERROR when previewable attachments exist and reader fails', () => {
    expect(
      decidePreviewState({
        attachments: [buildAttachment()],
        inlineContent: null,
        readerStatus: 'failed',
      }),
    ).toBe('ERROR')
  })

  it('returns ERROR when reader reports ready without previewable html content', () => {
    expect(
      decidePreviewState({
        attachments: [buildAttachment()],
        inlineContent: null,
        readerStatus: 'ready',
      }),
    ).toBe('ERROR')
  })
})
