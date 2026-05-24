import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import VisibilityBadge from './VisibilityBadge'

describe('VisibilityBadge', () => {
  it('renders company and client with distinct colors and icons', () => {
    render(
      <div className="space-y-2">
        <VisibilityBadge visibility="company" />
        <VisibilityBadge visibility="client" />
      </div>,
    )

    const companyBadge = screen.getByTitle('Visible to assigned companies + staff')
    const clientBadge = screen.getByTitle('Visible to assigned client companies + staff')

    expect(companyBadge).toHaveClass('bg-amber-50')
    expect(clientBadge).toHaveClass('bg-blue-50')

    const companyIconMarkup = companyBadge.querySelector('svg')?.innerHTML
    const clientIconMarkup = clientBadge.querySelector('svg')?.innerHTML
    expect(companyIconMarkup).toBeTruthy()
    expect(clientIconMarkup).toBeTruthy()
    expect(companyIconMarkup).not.toEqual(clientIconMarkup)
  })
})
