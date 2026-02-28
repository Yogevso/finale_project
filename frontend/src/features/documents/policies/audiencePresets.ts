import { normalizeAudienceFormPayload } from '@/features/documents/forms'
import type { DocumentVisibility } from '@/types'

export type AudiencePresetId = 'internal_staff' | 'public_broadcast' | 'company_targeted'

export interface AudiencePresetDefinition {
  id: AudiencePresetId
  label: string
  description: string
  visibility: DocumentVisibility
}

export interface AudiencePresetPayload {
  visibility: DocumentVisibility
  company_ids?: number[] | null
}

const AUDIENCE_PRESETS: readonly AudiencePresetDefinition[] = [
  {
    id: 'internal_staff',
    label: 'Internal Staff',
    description: 'Internal users only',
    visibility: 'internal',
  },
  {
    id: 'public_broadcast',
    label: 'Public Broadcast',
    description: 'Public and anonymous access',
    visibility: 'public',
  },
  {
    id: 'company_targeted',
    label: 'Company Targeted',
    description: 'Assigned companies and internal users',
    visibility: 'company',
  },
]

export function listAudiencePresets(): readonly AudiencePresetDefinition[] {
  return AUDIENCE_PRESETS
}

export function applyAudiencePreset(
  payload: AudiencePresetPayload,
  presetId: AudiencePresetId,
): { visibility: DocumentVisibility; company_ids: number[] } {
  const preset = AUDIENCE_PRESETS.find((item) => item.id === presetId)
  const normalized = normalizeAudienceFormPayload(payload)

  if (!preset) {
    return normalized
  }

  return {
    visibility: preset.visibility,
    company_ids: preset.visibility === 'company' ? normalized.company_ids : [],
  }
}
