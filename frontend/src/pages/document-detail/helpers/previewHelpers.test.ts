import { describe, expect, it } from 'vitest'
import {
  applyCommentHighlights,
  applyHighlights,
  clearCommentHighlights,
  clearHighlights,
  embedStoredTocSectionsInHtml,
  filterOutlineSectionsByHtml,
  getUsableVersionContent,
  mapOutlineItemsToSections,
  mergeTocSections,
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
      { id: 'toc-1', title: 'Intro', level: 1, page: 3, page_start: 3 },
    ])

    expect(sections[0]?.anchorId).toBe('page-3')
  })

  it('parses both generic and legacy page anchors', () => {
    expect(parsePageFromAnchorId('page-4')).toBe(4)
    expect(parsePageFromAnchorId('pdf-page-7')).toBe(7)
  })

  it('normalizes outline metadata and filters blank titles', () => {
    const sections = mapOutlineItemsToSections([
      { id: 'toc-blank', title: '  ', level: 0, page: 2, page_start: 2 },
      { id: 'toc-appendix', title: 'Appendix', level: 0, page: 5, page_start: 5, page_end: 7 },
      { id: 'toc-reader', title: 'Reader page', level: 3, anchor_id: 'reader-p9-node', page: 9, page_start: 9 },
    ])

    expect(sections).toEqual([
      {
        id: 'toc-appendix',
        text: 'Appendix',
        level: 1,
        html: '',
        index: 1,
        anchorId: 'page-5',
        pageStart: 5,
        pageEnd: 7,
      },
      {
        id: 'toc-reader',
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

  it('applies thread highlights to anchor text and clears them cleanly', () => {
    const container = document.createElement('div')
    container.innerHTML = '<p>Alpha beta gamma. Alpha beta delta.</p>'

    const applied = applyCommentHighlights(container, [
      { threadId: 41, anchorText: 'beta gamma' },
      { threadId: 42, anchorText: 'alpha   beta' },
    ])

    expect(applied).toHaveLength(2)
    expect(
      container.querySelector('span.doc-comment-highlight[data-comment-thread-id="41"]'),
    ).not.toBeNull()
    expect(
      container.querySelector('span.doc-comment-highlight[data-comment-thread-id="42"]'),
    ).not.toBeNull()

    clearCommentHighlights(container)
    expect(container.querySelectorAll('span.doc-comment-highlight')).toHaveLength(0)
    expect(container.textContent).toContain('Alpha beta gamma. Alpha beta delta.')
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

  it('keeps existing heading ids stable and assigns a unique id to inserted headings without ids', () => {
    const result = processHtmlIntoSections(
      '<article class="docx-document"><h2 id="heading-0">Intro</h2><p>Body</p><h2>Inserted</h2><p>Mid body</p><h2 id="heading-1">Next</h2><p>Tail</p></article>',
    )

    expect(result.sections).toHaveLength(3)
    expect(result.sections[0]?.anchorId).toBe('heading-0')
    expect(result.sections[2]?.anchorId).toBe('heading-1')
    expect(result.sections[1]?.anchorId).not.toBe('heading-0')
    expect(result.sections[1]?.anchorId).not.toBe('heading-1')
    expect(new Set(result.sections.map((section) => section.anchorId)).size).toBe(3)
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

  it('preserves nested inline toc entries after stripping the source contents block', () => {
    const result = processHtmlIntoSections(
      [
        '<article class="docx-document">',
        '<p>Contents</p>',
        '<ol>',
        '<li>Release Kit Summary 7',
        '<ol><li>Release Kit Details 7</li></ol>',
        '</li>',
        '<li>General Information 8</li>',
        '<li>Appendix A 75</li>',
        '</ol>',
        '<h1 id="heading-summary">Release Kit Summary</h1>',
        '<p>Summary body</p>',
        '<h2 id="heading-details">Release Kit Details</h2>',
        '<p>Details body</p>',
        '<h1 id="heading-appendix">Appendix A</h1>',
        '</article>',
      ].join(''),
    )

    expect(result.html).not.toContain('Contents')
    expect(result.sections.map((section) => section.text)).toEqual([
      'Release Kit Summary',
      'Release Kit Details',
      'General Information',
      'Appendix A',
    ])
    expect(result.sections.map((section) => section.level)).toEqual([1, 2, 1, 1])
    expect(result.sections[0]?.anchorId).toBe('heading-summary')
    expect(result.sections[1]?.anchorId).toBe('heading-details')
    expect(result.sections[2]?.anchorId).toBe('page-8')
    expect(result.sections[3]?.anchorId).toBe('heading-appendix')
  })

  it('preserves paragraph-based inline toc entries using toc level classes', () => {
    const result = processHtmlIntoSections(
      [
        '<article class="docx-document">',
        '<p>Contents</p>',
        '<p class="MsoToc1">Release Kit Summary 7</p>',
        '<p class="MsoToc2">Release Kit Details 7</p>',
        '<p class="MsoToc1">Appendix A 75</p>',
        '<h1 id="heading-summary">Release Kit Summary</h1>',
        '<p>Summary body</p>',
        '<h2 id="heading-details">Release Kit Details</h2>',
        '<p>Details body</p>',
        '<h1 id="heading-appendix">Appendix A</h1>',
        '</article>',
      ].join(''),
    )

    expect(result.sections.map((section) => section.text)).toEqual([
      'Release Kit Summary',
      'Release Kit Details',
      'Appendix A',
    ])
    expect(result.sections.map((section) => section.level)).toEqual([1, 2, 1])
    expect(result.sections[0]?.anchorId).toBe('heading-summary')
    expect(result.sections[1]?.anchorId).toBe('heading-details')
    expect(result.sections[2]?.anchorId).toBe('heading-appendix')
  })

  it('round-trips stored toc metadata without rendering the metadata block', () => {
    const persistedHtml = embedStoredTocSectionsInHtml(
      '<article class="docx-document"><h1 id="heading-summary">Release Kit Summary</h1><p>Summary body</p><h2 id="heading-details">Release Kit Details</h2><p>Details body</p><h1 id="heading-appendix">Appendix A</h1></article>',
      [
        {
          id: 'toc-0',
          text: 'Release Kit Summary',
          level: 1,
          html: '',
          index: 0,
          anchorId: 'page-7',
          pageStart: 7,
        },
        {
          id: 'toc-1',
          text: 'Release Kit Details',
          level: 2,
          html: '',
          index: 1,
          anchorId: 'page-7',
          pageStart: 7,
        },
        {
          id: 'toc-2',
          text: 'General Information',
          level: 1,
          html: '',
          index: 2,
          anchorId: 'page-8',
          pageStart: 8,
        },
        {
          id: 'toc-3',
          text: 'Appendix A',
          level: 1,
          html: '',
          index: 3,
          anchorId: 'page-75',
          pageStart: 75,
        },
      ],
    )

    expect(persistedHtml).toContain('doc-outline-metadata')

    const result = processHtmlIntoSections(persistedHtml)

    expect(result.html).not.toContain('doc-outline-metadata')
    expect(result.sections.map((section) => section.text)).toEqual([
      'Release Kit Summary',
      'Release Kit Details',
      'General Information',
      'Appendix A',
    ])
    expect(result.sections[0]?.anchorId).toBe('heading-summary')
    expect(result.sections[1]?.anchorId).toBe('heading-details')
    expect(result.sections[2]?.anchorId).toBe('page-8')
    expect(result.sections[3]?.anchorId).toBe('heading-appendix')
  })

  it('keeps backend TOC order while reusing html anchor ids for matching headings', () => {
    const outlineSections = mapOutlineItemsToSections([
      { id: 'toc-0', title: 'Intro', level: 1, page: 1, page_start: 1, anchor_id: 'page-1' },
      { id: 'toc-1', title: 'Status Summary', level: 1, page: 2, page_start: 2, anchor_id: 'page-2' },
      { id: 'toc-2', title: 'Reference Appendix', level: 1, page: 3, page_start: 3, anchor_id: 'page-3' },
    ])
    const htmlSections = processHtmlIntoSections(
      '<article class="docx-document"><h1 id="heading-intro">Intro</h1><p>Body</p><h2 id="heading-reference-appendix">Reference Appendix</h2><p>Appendix</p></article>',
    ).sections

    const merged = mergeTocSections(outlineSections, htmlSections)

    expect(merged.map((section) => section.text)).toEqual([
      'Intro',
      'Status Summary',
      'Reference Appendix',
    ])
    expect(merged[0]?.anchorId).toBe('heading-intro')
    expect(merged[1]?.anchorId).toBe('page-2')
    expect(merged[2]?.anchorId).toBe('heading-reference-appendix')
  })

  it('drops stale outline items that no longer match the current html while keeping outline-only matches', () => {
    const outlineSections = mapOutlineItemsToSections([
      { id: 'toc-0', title: 'Overview Notes', level: 2, page: 2, page_start: 2, anchor_id: 'page-2' },
      { id: 'toc-1', title: 'Obsolete Section', level: 2, page: 3, page_start: 3, anchor_id: 'page-3' },
      { id: 'toc-2', title: 'Reference Appendix', level: 2, page: 4, page_start: 4, anchor_id: 'page-4' },
    ])

    const filtered = filterOutlineSectionsByHtml(
      outlineSections,
      '<article class="docx-document"><p><strong>Overview Notes</strong></p><p>Body</p><h2 id="heading-appendix">Reference Appendix</h2><p>Appendix</p></article>',
    )

    expect(filtered.map((section) => section.text)).toEqual(['Overview Notes', 'Reference Appendix'])
    expect(filtered[1]?.anchorId).toBe('heading-appendix')
  })
})
