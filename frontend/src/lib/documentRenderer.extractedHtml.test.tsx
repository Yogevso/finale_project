import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { parseDocumentHtml } from '@/lib/documentRenderer'

const SAMPLE_EXTRACTED_DOCX_HTML =
  '<article class="docx-document" role="article" aria-label="Uploaded document">' +
  '<h1 class="extracted-heading extracted-heading-level-1" id="heading-wave-y-extractor-fixture">Wave Y Extractor Fixture</h1>' +
  '<p class="extracted-paragraph">This paragraph verifies <strong>bold</strong>, <em>italic</em>, <u>underline</u>, and <code class="extracted-code">build_wave_y()</code> extraction output.</p>' +
  '<ul class="extracted-list"><li>Upload DOCX through the management UI<ul><li>Verify semantic headings and lists</li></ul></li><li>Confirm responsive tables<ul><li>Check extracted images</li></ul></li></ul>' +
  '<div class="table-wrapper"><table class="extracted-table"><thead><tr><th colspan="2">Capability</th><th>Status</th></tr></thead><tbody><tr><td rowspan="2">DOCX extraction</td><td>Platform</td><td>Ready</td></tr><tr><td>Platform</td><td>Ready</td></tr></tbody></table></div>' +
  '<figure class="extracted-image"><img src="/files/wave-y-diagram.png" alt="Architecture snapshot" /><figcaption class="extracted-image-caption">Architecture snapshot</figcaption></figure>' +
  "</article>"

const SAMPLE_EXTRACTED_PPTX_HTML =
  '<div class="pptx-presentation" data-slide-count="2">' +
  '<section class="pptx-slide" id="slide-1" data-slide-number="1" aria-label="Slide 1: Wave Y Launch">' +
  '<span class="slide-badge" aria-label="Slide 1 of 2">Slide 1</span>' +
  '<h2 id="slide-1-title">Wave Y Launch</h2>' +
  '<p>Quarterly readiness review</p>' +
  '<ul class="slide-bullets"><li>DOCX uploads now extract cleanly</li><li><strong>PowerPoint decks</strong> render as vertical slides<ul><li>Warnings surface only when needed</li></ul></li></ul>' +
  '<details class="speaker-notes"><summary aria-expanded="false">Speaker Notes (click to expand)</summary><div class="notes-content"><p>Call out extraction confidence.</p></div></details>' +
  "</section>" +
  '<section class="pptx-slide" id="slide-2" data-slide-number="2" aria-label="Slide 2: Deployment Checklist">' +
  '<span class="slide-badge" aria-label="Slide 2 of 2">Slide 2</span>' +
  '<h2 id="slide-2-title">Deployment Checklist</h2>' +
  '<ol class="slide-bullets"><li>Upload the DOCX fixture</li><li>Verify table rendering</li><li>Confirm image lightbox<ol><li>Inspect mobile scroll behavior</li></ol></li></ol>' +
  "</section></div>"

describe('parseDocumentHtml rich extracted HTML', () => {
  it('renders a realistic extracted DOCX sample with tables and interactive images', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <MemoryRouter>{parseDocumentHtml(SAMPLE_EXTRACTED_DOCX_HTML)}</MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Wave Y Extractor Fixture' })).toBeInTheDocument()
    expect(screen.getByText('Verify semantic headings and lists')).toBeInTheDocument()
    expect(
      container.querySelector('.table-wrapper.document-table-scroll > table.extracted-table'),
    ).not.toBeNull()

    await user.click(screen.getByRole('button', { name: 'Architecture snapshot' }))

    const dialog = screen.getByRole('dialog', { name: 'Architecture snapshot' })
    expect(dialog).toHaveTextContent('Architecture snapshot')
  })

  it('renders a realistic extracted PPTX sample with slide sections and notes', () => {
    const { container } = render(
      <MemoryRouter>{parseDocumentHtml(SAMPLE_EXTRACTED_PPTX_HTML)}</MemoryRouter>,
    )

    expect(container.querySelectorAll('.pptx-slide')).toHaveLength(2)
    expect(screen.getByRole('heading', { name: 'Wave Y Launch' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Deployment Checklist' })).toBeInTheDocument()
    expect(screen.getByText('Warnings surface only when needed')).toBeInTheDocument()
    expect(screen.getByText('Inspect mobile scroll behavior')).toBeInTheDocument()
    expect(container.querySelector('details.speaker-notes')).not.toBeNull()
    expect(screen.getByText('Call out extraction confidence.')).toBeInTheDocument()
  })
})
