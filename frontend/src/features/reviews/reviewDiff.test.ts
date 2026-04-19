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
});
