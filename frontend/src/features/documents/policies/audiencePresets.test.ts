import { describe, expect, it } from 'vitest'

import { applyAudiencePreset, listAudiencePresets } from './audiencePresets'

describe('audience presets', () => {
  it('exposes stable audience presets', () => {
    expect(listAudiencePresets()).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'internal_staff', visibility: 'internal' }),
        expect.objectContaining({ id: 'public_broadcast', visibility: 'public' }),
        expect.objectContaining({ id: 'company_targeted', visibility: 'company' }),
      ]),
    )
  })

  it('clears company assignments for non-company presets', () => {
    expect(
      applyAudiencePreset(
        {
          visibility: 'company',
          company_ids: [5, 7],
        },
        'internal_staff',
      ),
    ).toEqual({
      visibility: 'internal',
      company_ids: [],
    })

    expect(
      applyAudiencePreset(
        {
          visibility: 'company',
          company_ids: [5, 7],
        },
        'public_broadcast',
      ),
    ).toEqual({
      visibility: 'public',
      company_ids: [],
    })
  })

  it('keeps normalized company assignments for company preset', () => {
    expect(
      applyAudiencePreset(
        {
          visibility: 'internal',
          company_ids: [6, 6, -1, 8],
        },
        'company_targeted',
      ),
    ).toEqual({
      visibility: 'company',
      company_ids: [6, 8],
    })
  })
})
