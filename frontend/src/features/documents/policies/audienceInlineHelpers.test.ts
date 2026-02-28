import { describe, expect, it } from 'vitest'

import {
  getAudienceDirtyHelperText,
  getAudienceVisibilityHelperText,
} from './audienceInlineHelpers'

describe('audience inline helpers', () => {
  it('returns visibility guidance for each audience type', () => {
    expect(getAudienceVisibilityHelperText('internal')).toContain('staff users only')
    expect(getAudienceVisibilityHelperText('public')).toContain('anonymous visitors')
    expect(getAudienceVisibilityHelperText('company')).toContain('Select at least one company')
    expect(getAudienceVisibilityHelperText('company', 'edit')).toContain('Use Details')
  })

  it('formats dirty-state helper text consistently', () => {
    expect(
      getAudienceDirtyHelperText({
        isDirty: false,
        visibilityChanged: false,
        companyAssignmentsChanged: false,
      }),
    ).toEqual({
      text: 'Audience matches the default audience for this flow.',
      isChanged: false,
    })

    expect(
      getAudienceDirtyHelperText({
        isDirty: true,
        visibilityChanged: true,
        companyAssignmentsChanged: false,
      }),
    ).toEqual({
      text: 'Audience updated: visibility changed.',
      isChanged: true,
    })

    expect(
      getAudienceDirtyHelperText({
        isDirty: true,
        visibilityChanged: false,
        companyAssignmentsChanged: true,
      }),
    ).toEqual({
      text: 'Audience updated: company assignments changed.',
      isChanged: true,
    })
  })
})
