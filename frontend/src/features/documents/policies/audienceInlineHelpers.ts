import type { AudienceDirtyState } from '@/features/documents/forms'
import type { DocumentVisibility } from '@/types'

export type AudienceHelperContext = 'compose' | 'edit'

export function getAudienceVisibilityHelperText(
  visibility: DocumentVisibility,
  context: AudienceHelperContext = 'compose',
): string {
  if (visibility === 'public') {
    return 'Public audience: anyone can access, including anonymous visitors.'
  }

  if (visibility === 'company') {
    if (context === 'edit') {
      return 'Company audience: assigned companies and staff. Use Details to manage assignments.'
    }
    return 'Company audience: assigned companies and staff. Select at least one company.'
  }

  return 'Internal audience: staff users only.'
}

export function getAudienceDirtyHelperText(
  dirtyState: AudienceDirtyState,
): { text: string; isChanged: boolean } {
  if (!dirtyState.isDirty) {
    return {
      text: 'Audience matches the default audience for this flow.',
      isChanged: false,
    }
  }

  if (dirtyState.visibilityChanged && dirtyState.companyAssignmentsChanged) {
    return {
      text: 'Audience updated: visibility and company assignments changed.',
      isChanged: true,
    }
  }

  if (dirtyState.visibilityChanged) {
    return {
      text: 'Audience updated: visibility changed.',
      isChanged: true,
    }
  }

  return {
    text: 'Audience updated: company assignments changed.',
    isChanged: true,
  }
}
