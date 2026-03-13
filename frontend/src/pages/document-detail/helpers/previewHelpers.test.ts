import { describe, expect, it } from 'vitest'
import {
  mapOutlineItemsToSections,
  parsePageFromAnchorId,
  processHtmlIntoSections,
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
})
