import { describe, expect, it } from 'vitest'

import {
  normalizeAudienceFormPayload,
  validateAudienceFormPayload,
} from './audienceSchema'

describe('audience schema', () => {
  it('normalizes visibility default and deduplicates valid company IDs', () => {
    const normalized = normalizeAudienceFormPayload({
      visibility: undefined,
      company_ids: [5, 5, -1, 8, 0],
    })

    expect(normalized).toEqual({
      visibility: 'internal',
      company_ids: [5, 8],
    })
  })

  it('fails validation when company visibility has no assignments', () => {
    const issue = validateAudienceFormPayload({
      visibility: 'company',
      company_ids: [],
    })

    expect(issue).toEqual({
      field: 'company_ids',
      message: 'Select at least one company for company-visible documents.',
      code: 'missing_company_assignment',
    })
  })

  it('fails validation when company IDs contain invalid values', () => {
    const issue = validateAudienceFormPayload({
      visibility: 'company',
      company_ids: [4, 0],
    })

    expect(issue).toEqual({
      field: 'company_ids',
      message: 'Company assignments contain invalid company IDs.',
      code: 'invalid_company_assignment',
    })
  })

  it('fails validation when non-company visibility includes assignments', () => {
    const issue = validateAudienceFormPayload({
      visibility: 'internal',
      company_ids: [3],
    })

    expect(issue).toEqual({
      field: 'company_ids',
      message: 'Company assignments are only allowed for company-visible documents.',
      code: 'invalid_company_assignment',
    })
  })

  it('passes validation for internal visibility without assignments', () => {
    const issue = validateAudienceFormPayload({
      visibility: 'internal',
      company_ids: [],
    })

    expect(issue).toBeNull()
  })
})
