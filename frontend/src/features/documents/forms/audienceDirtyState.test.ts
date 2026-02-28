import { describe, expect, it } from 'vitest'

import { getAudienceDirtyState } from './audienceDirtyState'

describe('getAudienceDirtyState', () => {
  it('returns not dirty when visibility and assignments are unchanged', () => {
    expect(
      getAudienceDirtyState(
        { visibility: 'internal', company_ids: [] },
        { visibility: 'internal', company_ids: [] },
      ),
    ).toEqual({
      isDirty: false,
      visibilityChanged: false,
      companyAssignmentsChanged: false,
    })
  })

  it('tracks visibility changes', () => {
    expect(
      getAudienceDirtyState(
        { visibility: 'internal', company_ids: [] },
        { visibility: 'public', company_ids: [] },
      ),
    ).toEqual({
      isDirty: true,
      visibilityChanged: true,
      companyAssignmentsChanged: false,
    })
  })

  it('tracks company assignment changes independent of order', () => {
    expect(
      getAudienceDirtyState(
        { visibility: 'company', company_ids: [2, 1] },
        { visibility: 'company', company_ids: [1, 2] },
      ),
    ).toEqual({
      isDirty: false,
      visibilityChanged: false,
      companyAssignmentsChanged: false,
    })

    expect(
      getAudienceDirtyState(
        { visibility: 'company', company_ids: [1, 2] },
        { visibility: 'company', company_ids: [1, 3] },
      ),
    ).toEqual({
      isDirty: true,
      visibilityChanged: false,
      companyAssignmentsChanged: true,
    })
  })
})
