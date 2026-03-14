/**
 * Y2-028: Component test for AnnouncementBanner
 * Render with message, verify displayed, dismiss, verify hidden, reload, verify still hidden.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AnnouncementBanner from '@/components/AnnouncementBanner'

// Mock publicApi
vi.mock('@/lib/publicApi', () => ({
  publicApi: {
    getAnnouncements: vi.fn().mockResolvedValue([
      { id: 1, message: 'Scheduled maintenance tonight', type: 'warning', is_active: true },
      { id: 2, message: 'New feature released!', type: 'success', is_active: true },
    ]),
  },
}))

describe('AnnouncementBanner (Y2-028)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders announcement messages', async () => {
    render(<AnnouncementBanner />)

    await waitFor(() => {
      expect(screen.getByText('Scheduled maintenance tonight')).toBeInTheDocument()
      expect(screen.getByText('New feature released!')).toBeInTheDocument()
    })
  })

  it('dismiss button hides the announcement', async () => {
    const user = userEvent.setup()
    render(<AnnouncementBanner />)

    await waitFor(() => {
      expect(screen.getByText('Scheduled maintenance tonight')).toBeInTheDocument()
    })

    // Dismiss the first announcement
    const dismissButtons = screen.getAllByRole('button', { name: /dismiss announcement/i })
    await user.click(dismissButtons[0])

    // First announcement should be gone
    expect(screen.queryByText('Scheduled maintenance tonight')).not.toBeInTheDocument()
    // Second should still be there
    expect(screen.getByText('New feature released!')).toBeInTheDocument()
  })

  it('dismissed announcement stays hidden after re-render', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<AnnouncementBanner />)

    await waitFor(() => {
      expect(screen.getByText('Scheduled maintenance tonight')).toBeInTheDocument()
    })

    // Dismiss
    const dismissButtons = screen.getAllByRole('button', { name: /dismiss announcement/i })
    await user.click(dismissButtons[0])
    expect(screen.queryByText('Scheduled maintenance tonight')).not.toBeInTheDocument()

    // Unmount and remount — simulates "reload"
    unmount()
    render(<AnnouncementBanner />)

    await waitFor(() => {
      expect(screen.getByText('New feature released!')).toBeInTheDocument()
    })

    // First announcement should still be hidden (persisted in localStorage)
    expect(screen.queryByText('Scheduled maintenance tonight')).not.toBeInTheDocument()
  })

  it('stores dismissed IDs in localStorage', async () => {
    const user = userEvent.setup()
    render(<AnnouncementBanner />)

    await waitFor(() => {
      expect(screen.getByText('Scheduled maintenance tonight')).toBeInTheDocument()
    })

    const dismissButtons = screen.getAllByRole('button', { name: /dismiss announcement/i })
    await user.click(dismissButtons[0])

    const stored = JSON.parse(localStorage.getItem('dismissed_announcements') || '[]')
    expect(stored).toContain(1)
  })
})
