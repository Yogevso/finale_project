import type { DocumentVisibility } from '@/types'

export type AudienceVisibility = DocumentVisibility

export type AudienceFormPayload = {
  visibility?: AudienceVisibility | null
  company_ids?: number[] | null
}

export type NormalizedAudienceFormPayload = {
  visibility: AudienceVisibility
  company_ids: number[]
}

export type AudienceValidationIssue = {
  field: 'visibility' | 'company_ids'
  message: string
  code: 'missing_company_assignment' | 'invalid_company_assignment'
}
