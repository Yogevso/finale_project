import { describe, expect, it } from 'vitest'

import {
  normalizeCommaSeparatedInput,
  normalizeFileStem,
  normalizeMultilineInput,
  normalizeSingleLineInput,
} from './uiInputRules'

describe('uiInputRules', () => {
  it('normalizes single-line values by trimming and collapsing whitespace', () => {
    expect(normalizeSingleLineInput('  Safety \n\t Manual   2026  ', 160)).toBe('Safety Manual 2026')
  })

  it('normalizes multiline values while preserving intended line breaks', () => {
    expect(normalizeMultilineInput('  First line.  \r\n\r\n\r\nSecond line.   ', 160)).toBe(
      'First line.\n\nSecond line.',
    )
  })

  it('normalizes comma-separated values, removes duplicates, and respects length limits', () => {
    expect(normalizeCommaSeparatedInput('ops, guide, Ops, onboarding', 18)).toBe('ops, guide')
  })

  it('builds a normalized title from a file stem', () => {
    expect(normalizeFileStem('  Release Notes 2026 .docx ', 160)).toBe('Release Notes 2026')
  })
})
