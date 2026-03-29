import { describe, expect, it } from 'vitest'

import {
  NO_DOCUMENT_DESCRIPTION_LABEL,
  UNTITLED_DOCUMENT_LABEL,
  getDocumentDisplayDescription,
  getDocumentDisplayTitle,
} from './documentDisplay'

describe('documentDisplay', () => {
  it('normalizes empty and whitespace-only titles', () => {
    expect(getDocumentDisplayTitle(undefined)).toBe(UNTITLED_DOCUMENT_LABEL)
    expect(getDocumentDisplayTitle(null)).toBe(UNTITLED_DOCUMENT_LABEL)
    expect(getDocumentDisplayTitle('')).toBe(UNTITLED_DOCUMENT_LABEL)
    expect(getDocumentDisplayTitle('   \n\t  ')).toBe(UNTITLED_DOCUMENT_LABEL)
  })

  it('preserves long titles after trimming outer whitespace', () => {
    const longTitle =
      '   Quarterly platform rollout guide with customer-specific notes and an exceptionally-long-unbroken-token-ABCDEFGHIJKLmnopqrstuvwxyz0123456789   '

    expect(getDocumentDisplayTitle(longTitle)).toBe(
      'Quarterly platform rollout guide with customer-specific notes and an exceptionally-long-unbroken-token-ABCDEFGHIJKLmnopqrstuvwxyz0123456789',
    )
  })

  it('normalizes empty and whitespace-only descriptions', () => {
    expect(getDocumentDisplayDescription(undefined)).toBe(NO_DOCUMENT_DESCRIPTION_LABEL)
    expect(getDocumentDisplayDescription(null)).toBe(NO_DOCUMENT_DESCRIPTION_LABEL)
    expect(getDocumentDisplayDescription('')).toBe(NO_DOCUMENT_DESCRIPTION_LABEL)
    expect(getDocumentDisplayDescription(' \n \t ')).toBe(NO_DOCUMENT_DESCRIPTION_LABEL)
  })

  it('preserves multiline descriptions after trimming outer whitespace', () => {
    const multilineDescription = '  First line.\nSecond line with details.\n\nFinal note.  '

    expect(getDocumentDisplayDescription(multilineDescription)).toBe(
      'First line.\nSecond line with details.\n\nFinal note.',
    )
  })
})
