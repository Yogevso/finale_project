import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ContentEditChooserPopup } from '@/pages/document-detail/components/ContentEditChooserPopup'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'

const sections: TocSection[] = [
  {
    id: 'intro',
    text: 'Introduction',
    level: 2,
    html: '<h2>Introduction</h2><p>Body</p>',
    index: 0,
    anchorId: 'heading-0',
  },
  {
    id: 'scope',
    text: 'Overview Notes',
    level: 2,
    html: '<h2>Overview Notes</h2><table><tbody><tr><td>Cell</td></tr></tbody></table>',
    index: 1,
    anchorId: 'heading-1',
  },
]

describe('ContentEditChooserPopup', () => {
  it('offers a full document editor option for complex content', async () => {
    const user = userEvent.setup()
    const onEditFullDocument = vi.fn()

    render(
      <ContentEditChooserPopup
        sections={sections}
        onClose={vi.fn()}
        onEditFullDocument={onEditFullDocument}
        onEditSection={vi.fn()}
        onAddSection={vi.fn()}
      />,
    )

    expect(
      screen.getByText(/use this when you need to edit tables, mixed layouts, or content that spans multiple sections/i),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /open full document editor/i }))

    expect(onEditFullDocument).toHaveBeenCalledTimes(1)
  })
})
