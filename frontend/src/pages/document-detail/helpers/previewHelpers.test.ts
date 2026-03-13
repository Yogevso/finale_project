import { describe, expect, it } from 'vitest'
import {
  applyHighlights,
  clearHighlights,
  getUsableVersionContent,
  mapOutlineItemsToSections,
  parsePageFromAnchorId,
  processHtmlIntoSections,
  resolveSectionPageStart,
} from '@/pages/document-detail/helpers/previewHelpers'

describe('processHtmlIntoSections', () => {
  it('extracts sections from DOCX article wrappers', () => {
    const result = processHtmlIntoSections(
      '<article class="docx-document"><h1 id="heading-intro">Intro</h1><p>Paragraph</p><h2 id="heading-details">Details</h2><p>More</p></article>',
    )

    expect(result.sections).toHaveLength(2)
    expect(result.sections[0]?.anchorId).toBe('heading-intro')
    expect(result.sections[1]?.anchorId).toBe('heading-details')
  })

  it('extracts slide sections from PPTX presentation wrappers', () => {
    const result = processHtmlIntoSections(
      '<div class="pptx-presentation" data-slide-count="2"><section class="pptx-slide" id="slide-1"><h2 id="slide-1-title">Welcome</h2><p>Body</p></section><section class="pptx-slide" id="slide-2"><h2 id="slide-2-title">Roadmap</h2><p>Body</p></section></div>',
    )

    expect(result.sections).toHaveLength(2)
    expect(result.sections[0]?.text).toBe('Welcome')
    expect(result.sections[0]?.anchorId).toBe('slide-1-title')
    expect(result.sections[1]?.text).toBe('Roadmap')
  })

  it('uses generic page anchors for outline items', () => {
    const sections = mapOutlineItemsToSections([
      { id: 'toc-1', title: 'Intro', level: 1, page_start: 3 },
    ])

    expect(sections[0]?.anchorId).toBe('page-3')
  })

  it('parses both generic and legacy page anchors', () => {
    expect(parsePageFromAnchorId('page-4')).toBe(4)
    expect(parsePageFromAnchorId('pdf-page-7')).toBe(7)
  })

  it('normalizes outline metadata and filters blank titles', () => {
    const sections = mapOutlineItemsToSections([
      { title: '  ', level: 0, page: 2 },
      { title: 'Appendix', level: 0, page: 5, page_end: 7 },
      { title: 'Reader page', level: 3, anchor_id: 'reader-p9-node', page_start: 9 },
    ])

    expect(sections).toEqual([
      {
        id: 'toc-1',
        text: 'Appendix',
        level: 1,
        html: '',
        index: 1,
        anchorId: 'page-5',
        pageStart: 5,
        pageEnd: 7,
      },
      {
        id: 'toc-2',
        text: 'Reader page',
        level: 3,
        html: '',
        index: 2,
        anchorId: 'reader-p9-node',
        pageStart: 9,
        pageEnd: null,
      },
    ])
  })

  it('resolves page numbers from explicit values and reader-style anchors', () => {
    expect(resolveSectionPageStart({ id: 'a', text: 'A', level: 1, html: '', index: 0, pageStart: 6 })).toBe(6)
    expect(
      resolveSectionPageStart({
        id: 'b',
        text: 'B',
        level: 1,
        html: '',
        index: 1,
        anchorId: 'reader-p12-node',
      }),
    ).toBe(12)
    expect(parsePageFromAnchorId('page-zero')).toBeNull()
    expect(parsePageFromAnchorId(null)).toBeNull()
  })

  it('treats placeholder upload text as unusable version content', () => {
    expect(getUsableVersionContent('  uploaded from file: release.docx  ')).toBeNull()
    expect(getUsableVersionContent('   ')).toBeNull()
    expect(getUsableVersionContent('<p>Real content</p>')).toBe('<p>Real content</p>')
  })

  it('adds and clears literal search highlights without nesting marks', () => {
    const container = document.createElement('div')
    container.innerHTML = '<p>Regex chars .* are literal. Regex chars .* stay literal.</p>'

    applyHighlights(container, 'chars .*')

    const marks = container.querySelectorAll('mark.doc-highlight')
    expect(marks).toHaveLength(2)
    expect(marks[0]?.textContent).toBe('chars .*')

    applyHighlights(container, 'literal')
    expect(container.querySelectorAll('mark.doc-highlight')).toHaveLength(2)
    expect(container.textContent).toContain('Regex chars .* are literal.')

    clearHighlights(container)
    expect(container.querySelectorAll('mark.doc-highlight')).toHaveLength(0)
    expect(container.textContent).toContain('Regex chars .* stay literal.')
  })

  it('creates a fallback document section when sanitized html has no headings', () => {
    const result = processHtmlIntoSections(
      '<div><p>Summary only</p><ul><li>Bullet</li></ul></div>',
    )

    expect(result.sections).toEqual([
      expect.objectContaining({
        id: 'section-0-full-document',
        text: 'Document Content',
        anchorId: 'document-content-area',
      }),
    ])
  })

  it('treats lower-level headings as sections when no primary headings exist', () => {
    const result = processHtmlIntoSections(
      '<article class="docx-document"><h4>Appendix</h4><p>Body</p><h5>Appendix B</h5><p>More</p></article>',
    )

    expect(result.sections).toHaveLength(2)
    expect(result.sections[0]?.anchorId).toBe('heading-0')
    expect(result.sections[0]?.level).toBe(4)
    expect(result.sections[1]?.anchorId).toBe('heading-1')
    expect(result.sections[1]?.level).toBe(5)
  })

  it('uses slide fallbacks when a PPTX slide has no heading element', () => {
    const result = processHtmlIntoSections(
      '<div class="pptx-presentation"><section class="pptx-slide" id="slide-1"><p>No title</p></section></div>',
    )

    expect(result.sections).toEqual([
      expect.objectContaining({
        text: 'Slide 1',
        anchorId: 'slide-1',
        level: 2,
      }),
    ])
  })
})
