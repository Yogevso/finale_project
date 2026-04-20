import { describe, expect, it } from 'vitest';

import { buildReviewDiffModel } from './reviewDiff';

describe('buildReviewDiffModel', () => {
  it('builds a merged toc with modified, removed, and added sections', () => {
    const previousHtml = `
      <h1>Overview</h1>
      <p>Previous introduction</p>
      <h2>Legacy Section</h2>
      <p>Legacy content</p>
    `;
    const currentHtml = `
      <h1>Overview</h1>
      <p>Updated introduction</p>
      <h2>New Section</h2>
      <p>Brand new content</p>
    `;

    const model = buildReviewDiffModel({
      previousHtml,
      currentHtml,
      tocItems: [
        { id: 'toc-overview', title: 'Overview', level: 1, page: 1, page_start: 1 },
        { id: 'toc-new', title: 'New Section', level: 2, page: 2, page_start: 2 },
      ],
    });

    expect(model.summary.modified).toBe(1);
    expect(model.summary.added).toBe(1);
    expect(model.summary.removed).toBe(1);
    expect(model.changedEntries.map((entry) => `${entry.title}:${entry.status}`)).toEqual([
      'Overview:modified',
      'Legacy Section:removed',
      'New Section:added',
    ]);
  });

  it('treats adjacent remove+add with similar content as a modified section', () => {
    const previousHtml = `
      <h2>System Overview</h2>
      <p>The platform routes release artifacts through a controlled workflow.</p>
    `;
    const currentHtml = `
      <h2>System Architecture Overview</h2>
      <p>The platform routes release artifacts through a controlled workflow with policy checks.</p>
    `;

    const model = buildReviewDiffModel({ previousHtml, currentHtml });

    expect(model.summary.modified).toBe(1);
    expect(model.summary.added).toBe(0);
    expect(model.summary.removed).toBe(0);
    expect(model.changedEntries[0]?.status).toBe('modified');
  });

  it('treats section-number matches as modified even when titles changed', () => {
    const previousHtml = `
      <h2>2.1 Current Situation (As-Is)</h2>
      <p>The current process depends on manual communication.</p>
      <h2>3.0 Next Section</h2>
      <p>Stable body</p>
    `;
    const currentHtml = `
      <h2>2.1 Current Situation (As-Is)try</h2>
      <p>The current process depends on manual communication with policy checks.</p>
      <h2>3.0 Next Section</h2>
      <p>Stable body</p>
    `;

    const model = buildReviewDiffModel({ previousHtml, currentHtml });

    expect(model.summary.modified).toBe(1);
    expect(model.summary.added).toBe(0);
    expect(model.summary.removed).toBe(0);
    expect(model.changedEntries).toHaveLength(1);
    expect(model.changedEntries[0]?.status).toBe('modified');
    expect(model.changedEntries[0]?.title).toContain('2.1');
  });

  it('does not collapse non-adjacent remove+add pairs without section-number evidence', () => {
    const previousHtml = `
      <h1>Alpha Report Final Project11111</h1>
      <p>Old introduction text.</p>
      <h2>Elevator Pitch / Abstract</h2>
      <p>Legacy elevator section text.</p>
    `;
    const currentHtml = `
      <h1>Alpha Report Final Project43w</h1>
      <p>Updated introduction text with new details.</p>
      <h2>New Section</h2>
      <p>Brand new section content.</p>
    `;

    const model = buildReviewDiffModel({ previousHtml, currentHtml });

    expect(model.summary.modified).toBe(0);
    expect(model.summary.added).toBe(2);
    expect(model.summary.removed).toBe(2);
  });
});
