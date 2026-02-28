import type {
  AudienceFormPayload,
  AudienceValidationIssue,
  NormalizedAudienceFormPayload,
} from './audienceFormTypes'

const DEFAULT_VISIBILITY = 'internal'

function normalizeCompanyIds(companyIds?: number[] | null): number[] {
  if (!companyIds || companyIds.length === 0) {
    return []
  }

  const deduped = Array.from(new Set(companyIds))
  return deduped.filter((companyId) => Number.isInteger(companyId) && companyId > 0)
}

function hasInvalidCompanyIds(companyIds?: number[] | null): boolean {
  if (!companyIds || companyIds.length === 0) {
    return false
  }

  return companyIds.some((companyId) => !Number.isInteger(companyId) || companyId <= 0)
}

export function normalizeAudienceFormPayload(
  payload: AudienceFormPayload,
): NormalizedAudienceFormPayload {
  return {
    visibility: payload.visibility ?? DEFAULT_VISIBILITY,
    company_ids: normalizeCompanyIds(payload.company_ids),
  }
}

export function validateAudienceFormPayload(
  payload: AudienceFormPayload,
): AudienceValidationIssue | null {
  const normalized = normalizeAudienceFormPayload(payload)

  if (hasInvalidCompanyIds(payload.company_ids)) {
    return {
      field: 'company_ids',
      message: 'Company assignments contain invalid company IDs.',
      code: 'invalid_company_assignment',
    }
  }

  if (normalized.visibility === 'company' && normalized.company_ids.length === 0) {
    return {
      field: 'company_ids',
      message: 'Select at least one company for company-visible documents.',
      code: 'missing_company_assignment',
    }
  }

  if (normalized.visibility !== 'company' && normalized.company_ids.length > 0) {
    return {
      field: 'company_ids',
      message: 'Company assignments are only allowed for company-visible documents.',
      code: 'invalid_company_assignment',
    }
  }

  return null
}
