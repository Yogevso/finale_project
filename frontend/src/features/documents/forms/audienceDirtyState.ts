import type { AudienceFormPayload } from './audienceFormTypes'
import { normalizeAudienceFormPayload } from './audienceSchema'

export type AudienceDirtyState = {
  isDirty: boolean
  visibilityChanged: boolean
  companyAssignmentsChanged: boolean
}

function toComparableCompanyIds(companyIds: number[]): string {
  return [...companyIds].sort((left, right) => left - right).join(',')
}

export function getAudienceDirtyState(
  initialPayload: AudienceFormPayload,
  currentPayload: AudienceFormPayload,
): AudienceDirtyState {
  const initial = normalizeAudienceFormPayload(initialPayload)
  const current = normalizeAudienceFormPayload(currentPayload)

  const visibilityChanged = initial.visibility !== current.visibility
  const companyAssignmentsChanged =
    toComparableCompanyIds(initial.company_ids) !== toComparableCompanyIds(current.company_ids)

  return {
    isDirty: visibilityChanged || companyAssignmentsChanged,
    visibilityChanged,
    companyAssignmentsChanged,
  }
}
