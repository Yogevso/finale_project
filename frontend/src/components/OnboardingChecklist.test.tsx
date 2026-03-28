import { fireEvent, render, screen } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import OnboardingChecklist from '@/components/OnboardingChecklist'
import type { OnboardingStep } from '@/features/onboarding/config'

const steps: OnboardingStep[] = [
  {
    id: 'open_documents',
    title: 'Open documents',
    description: 'Review the documents workspace.',
    href: '/documents',
    hrefLabel: 'Go to documents',
  },
  {
    id: 'open_profile',
    title: 'Open profile',
    description: 'Review your settings.',
    href: '/profile',
    hrefLabel: 'Go to profile',
  },
]

function renderChecklist(overrides: Partial<ComponentProps<typeof OnboardingChecklist>> = {}) {
  const onToggleCollapsed = vi.fn()
  const onToggleStep = vi.fn()
  const onReset = vi.fn()
  const onOpenGuide = vi.fn()

  render(
    <MemoryRouter>
      <OnboardingChecklist
        title="Welcome checklist"
        description="Use these steps to get familiar with the workspace."
        steps={steps}
        completedSteps={[]}
        onToggleCollapsed={onToggleCollapsed}
        onToggleStep={onToggleStep}
        onReset={onReset}
        onOpenGuide={onOpenGuide}
        {...overrides}
      />
    </MemoryRouter>,
  )

  return {
    onToggleCollapsed,
    onToggleStep,
    onReset,
    onOpenGuide,
  }
}

describe('OnboardingChecklist', () => {
  it('renders steps and forwards guide/reset/toggle actions', () => {
    const { onToggleStep, onReset, onOpenGuide } = renderChecklist()

    expect(screen.getByText('Welcome checklist')).toBeInTheDocument()
    expect(screen.getByText('Open documents')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Mark Open documents complete'))
    expect(onToggleStep).toHaveBeenCalledWith('open_documents')

    fireEvent.click(screen.getByRole('button', { name: 'Reopen guide' }))
    expect(onOpenGuide).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: /reset/i }))
    expect(onReset).toHaveBeenCalledTimes(1)
  })

  it('shows a compact reminder when collapsed and incomplete', () => {
    const { onToggleCollapsed } = renderChecklist({ isCollapsed: true })

    expect(screen.getByText(/steps completed/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Expand checklist' }))
    expect(onToggleCollapsed).toHaveBeenCalledTimes(1)
  })

  it('shows the completion state when every step is done', () => {
    renderChecklist({
      completedSteps: steps.map((step) => step.id),
      completionDate: '2026-03-28T10:00:00Z',
    })

    expect(screen.getByText('Checklist completed')).toBeInTheDocument()
    expect(screen.getByText(/completed on/i)).toBeInTheDocument()
  })
})
