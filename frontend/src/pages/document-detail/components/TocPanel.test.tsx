import type { ComponentProps } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as clipboardEnv from '@/env/clipboard'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { TocPanel } from './TocPanel'

const toastSuccessMock = vi.fn()
const toastErrorMock = vi.fn()

vi.mock('@/env/clipboard', () => ({
  writeText: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: (...args: unknown[]) => toastErrorMock(...args),
  },
}))

const clipboardWriteTextMock = vi.mocked(clipboardEnv.writeText)

const sections: TocSection[] = [
  {
    id: 'intro',
    text: 'Introduction',
    level: 1,
    html: '<h1>Introduction</h1>',
    index: 0,
    anchorId: 'intro',
    pageStart: 1,
  },
  {
    id: 'details',
    text: 'Release Details',
    level: 2,
    html: '<h2>Release Details</h2>',
    index: 1,
    anchorId: 'reader-p6-node',
    pageStart: 6,
  },
]

function renderTocPanel(overrides: Partial<ComponentProps<typeof TocPanel>> = {}) {
  return render(
    <TocPanel
      sections={sections}
      tocCollapsed={false}
      onToggleCollapsed={() => undefined}
      activeHeading="intro"
      readerCurrentPage={1}
      isEditor
      showingReaderView={false}
      sectionLinkBasePath="/documents/42/fullscreen"
      onSectionClick={() => undefined}
      onEditSection={() => undefined}
      {...overrides}
    />,
  )
}

describe('TocPanel', () => {
  beforeEach(() => {
    clipboardWriteTextMock.mockReset()
    clipboardWriteTextMock.mockResolvedValue(undefined)
    toastSuccessMock.mockReset()
    toastErrorMock.mockReset()
  })

  it('copies a section link using the current document origin and shows success feedback', async () => {
    const user = userEvent.setup()
    renderTocPanel()

    await user.click(screen.getByLabelText('Copy link to Introduction'))

    const expectedUrl = new URL('/documents/42/fullscreen#intro', window.location.origin).toString()
    expect(clipboardWriteTextMock).toHaveBeenCalledWith(expectedUrl)
    expect(toastSuccessMock).toHaveBeenCalledWith('Section link copied')
    expect(toastErrorMock).not.toHaveBeenCalled()
  })

  it('shows an error toast when copying a section link fails', async () => {
    clipboardWriteTextMock.mockRejectedValueOnce(new Error('clipboard denied'))
    const user = userEvent.setup()
    renderTocPanel()

    await user.click(screen.getByLabelText('Copy link to Introduction'))

    expect(toastErrorMock).toHaveBeenCalledWith('Failed to copy section link')
    expect(toastSuccessMock).not.toHaveBeenCalled()
  })

  it('shows the active section label in collapsed mode using the current reader page', () => {
    renderTocPanel({
      tocCollapsed: true,
      activeHeading: null,
      showingReaderView: true,
      readerCurrentPage: 6,
    })

    expect(screen.getByText('Release Details')).toBeInTheDocument()
  })

  it('exposes long section labels without relying on truncation-only rendering', () => {
    renderTocPanel({
      sections: [
        {
          id: 'long-label',
          text: 'A very long subsection title that should stay readable inside the toc panel',
          level: 2,
          html: '<h2>Long section</h2>',
          index: 0,
          anchorId: 'long-section',
          pageStart: 2,
        },
      ],
    })

    expect(
      screen.getByTitle('A very long subsection title that should stay readable inside the toc panel'),
    ).toBeInTheDocument()
  })
})

describe('TocPanel numbering', () => {
  const numbered: TocSection[] = [
    { id: 'a', text: '1 Release Kit Summary', level: 1, html: '', index: 0, anchorId: 'a', pageStart: 1 },
    { id: 'b', text: 'yejim', level: 2, html: '', index: 1, anchorId: 'b', pageStart: 1 },
    { id: 'c', text: '1.1 Release Kit Details', level: 2, html: '', index: 2, anchorId: 'c', pageStart: 2 },
    { id: 'd', text: '2 General Information', level: 1, html: '', index: 3, anchorId: 'd', pageStart: 3 },
  ]

  it("shows the document's own numbering once, not beside a positional count", () => {
    // The rail used to render "1.2" next to a heading the document calls "1.1", because
    // the unnumbered section ahead of it had taken slot 1.1.
    renderTocPanel({ sections: numbered, activeHeading: 'a' })

    const entry = screen.getByTitle('1.1 Release Kit Details')
    expect(entry.textContent).toBe('1.1Release Kit Details')
    expect(entry.textContent).not.toContain('1.21.1')
  })

  it('leaves an unnumbered heading unnumbered rather than contradicting its neighbours', () => {
    renderTocPanel({ sections: numbered, activeHeading: 'a' })

    expect(screen.getByTitle('yejim').textContent).toBe('yejim')
  })

  it('still counts positions for a document that numbers nothing', () => {
    renderTocPanel()

    expect(screen.getByTitle('Release Details').textContent).toBe('1.1Release Details')
  })
})
