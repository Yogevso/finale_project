import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import OnboardingGuideDialog from '@/components/OnboardingGuideDialog'
import { getOnboardingConfig } from '@/features/onboarding/config'

describe('OnboardingGuideDialog', () => {
  it('renders the welcome guide content and closes from the action button', () => {
    const onClose = vi.fn()

    render(
      <MemoryRouter>
        <OnboardingGuideDialog
          open
          config={getOnboardingConfig('editor')}
          onClose={onClose}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('dialog', { name: 'Welcome guide' })).toBeInTheDocument()
    expect(screen.getByText('Welcome to the editor workflow')).toBeInTheDocument()
    expect(screen.getByText('What to expect')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Start checklist' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
