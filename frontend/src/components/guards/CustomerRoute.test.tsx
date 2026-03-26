import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import CustomerRoute from './CustomerRoute'

const roleGuardPropsSpy = vi.hoisted(() => vi.fn())

vi.mock('./RoleGuard', () => ({
  CustomerGuard: ({ children }: { children: ReactNode }) => {
    roleGuardPropsSpy({ delegated: true })
    return <div data-testid="customer-guard">{children}</div>
  },
}))

describe('CustomerRoute', () => {
  it('delegates customer portal protection to the shared guard implementation', () => {
    render(
      <CustomerRoute>
        <div>Portal content</div>
      </CustomerRoute>,
    )

    expect(screen.getByTestId('customer-guard')).toBeInTheDocument()
    expect(screen.getByText('Portal content')).toBeInTheDocument()
    expect(roleGuardPropsSpy).toHaveBeenCalledWith({ delegated: true })
  })
})
