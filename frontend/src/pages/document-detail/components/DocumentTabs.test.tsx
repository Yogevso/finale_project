import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DocumentTabs } from '@/pages/document-detail/components/DocumentTabs'

describe('DocumentTabs', () => {
  it('renders badge counts and changes tabs when a tab is clicked', async () => {
    const user = userEvent.setup()
    const onTabChange = vi.fn()

    render(
      <DocumentTabs
        activeTab="preview"
        onTabChange={onTabChange}
        counts={{ comments: 6, attachments: 3, versions: 4 }}
      />,
    )

    expect(screen.getByRole('button', { name: 'Versions (4)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Attachments (3)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Comments (6)' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Comments (6)' }))

    expect(onTabChange).toHaveBeenCalledWith('comments')
  })
})
