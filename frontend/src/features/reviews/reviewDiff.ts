import { buildVersionDiffRows, type VersionDiffRow } from '@/lib/versionDiff';
import {
  filterOutlineSectionsByHtml,
  mapOutlineItemsToSections,
  mergeTocSections,
  processHtmlIntoSections,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers';
import type { AttachmentOutlineItem } from '@/types';

export type ReviewSectionStatus = 'unchanged' | 'modified' | 'added' | 'removed';

export interface ReviewDiffEntry {
  id: string;
  title: string;
  level: number;
  status: ReviewSectionStatus;
  previousHtml: string | null;
  currentHtml: string | null;
  diffRows: VersionDiffRow[];
  anchorId?: string;
  pageStart?: number;
  pageEnd?: number | null;
}

export interface ReviewDiffModel {
  tocEntries: ReviewDiffEntry[];
  changedEntries: ReviewDiffEntry[];
  summary: {
    unchanged: number;
    modified: number;
    added: number;
    removed: number;
  };
}

function normalizeSectionTitle(value: string | undefined): string {
  return (value || '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function buildOccurrenceAwareKeys(sections: TocSection[]): string[] {
  const counts = new Map<string, number>();

  return sections.map((section) => {
    const baseKey = normalizeSectionTitle(section.text) || `section-${section.index}`;
    const nextCount = (counts.get(baseKey) || 0) + 1;
    counts.set(baseKey, nextCount);
    return `${baseKey}::${nextCount}`;
  });
}

function buildLcsMatrix(left: string[], right: string[]): number[][] {
  const matrix = Array.from({ length: left.length + 1 }, () =>
    Array<number>(right.length + 1).fill(0)
  );

  for (let leftIndex = left.length - 1; leftIndex >= 0; leftIndex -= 1) {
    for (let rightIndex = right.length - 1; rightIndex >= 0; rightIndex -= 1) {
      matrix[leftIndex][rightIndex] =
        left[leftIndex] === right[rightIndex]
          ? matrix[leftIndex + 1][rightIndex + 1] + 1
          : Math.max(matrix[leftIndex + 1][rightIndex], matrix[leftIndex][rightIndex + 1]);
    }
  }

  return matrix;
}

function createDiffEntry(
  previousSection: TocSection | null,
  currentSection: TocSection | null
): ReviewDiffEntry {
  const diffRows = buildVersionDiffRows(previousSection?.html || '', currentSection?.html || '');
  let status: ReviewSectionStatus;

  if (previousSection && currentSection) {
    status = diffRows.some((row) => row.status !== 'unchanged') ? 'modified' : 'unchanged';
  } else if (currentSection) {
    status = 'added';
  } else {
    status = 'removed';
  }

  const sourceSection = currentSection || previousSection;

  return {
    id: sourceSection?.id || `review-section-${status}`,
    title: sourceSection?.text || 'Untitled section',
    level: sourceSection?.level || 1,
    status,
    previousHtml: previousSection?.html || null,
    currentHtml: currentSection?.html || null,
    diffRows,
    anchorId: currentSection?.anchorId || previousSection?.anchorId,
    pageStart: currentSection?.pageStart || previousSection?.pageStart,
    pageEnd: currentSection?.pageEnd ?? previousSection?.pageEnd ?? null,
  };
}

function buildMergedTocEntries(
  previousSections: TocSection[],
  currentSections: TocSection[]
): ReviewDiffEntry[] {
  const previousKeys = buildOccurrenceAwareKeys(previousSections);
  const currentKeys = buildOccurrenceAwareKeys(currentSections);
  const matrix = buildLcsMatrix(previousKeys, currentKeys);
  const entries: ReviewDiffEntry[] = [];

  let previousIndex = 0;
  let currentIndex = 0;

  while (previousIndex < previousKeys.length && currentIndex < currentKeys.length) {
    if (previousKeys[previousIndex] === currentKeys[currentIndex]) {
      entries.push(createDiffEntry(previousSections[previousIndex], currentSections[currentIndex]));
      previousIndex += 1;
      currentIndex += 1;
      continue;
    }

    if (matrix[previousIndex + 1][currentIndex] >= matrix[previousIndex][currentIndex + 1]) {
      entries.push(createDiffEntry(previousSections[previousIndex], null));
      previousIndex += 1;
    } else {
      entries.push(createDiffEntry(null, currentSections[currentIndex]));
      currentIndex += 1;
    }
  }

  while (previousIndex < previousSections.length) {
    entries.push(createDiffEntry(previousSections[previousIndex], null));
    previousIndex += 1;
  }

  while (currentIndex < currentSections.length) {
    entries.push(createDiffEntry(null, currentSections[currentIndex]));
    currentIndex += 1;
  }

  return entries;
}

function resolveCurrentSections(
  currentHtml: string | null | undefined,
  tocItems: AttachmentOutlineItem[] = []
): TocSection[] {
  if (!currentHtml?.trim()) {
    return [];
  }

  const htmlSections = processHtmlIntoSections(currentHtml).sections;

  if (tocItems.length === 0) {
    return htmlSections;
  }

  const outlineSections = filterOutlineSectionsByHtml(
    mapOutlineItemsToSections(tocItems),
    currentHtml
  );

  if (outlineSections.length === 0) {
    return htmlSections;
  }

  return mergeTocSections(outlineSections, htmlSections);
}

export function buildReviewDiffModel({
  previousHtml,
  currentHtml,
  tocItems = [],
}: {
  previousHtml?: string | null;
  currentHtml?: string | null;
  tocItems?: AttachmentOutlineItem[];
}): ReviewDiffModel {
  const previousSections = previousHtml?.trim()
    ? processHtmlIntoSections(previousHtml).sections
    : [];
  const currentSections = resolveCurrentSections(currentHtml, tocItems);
  const tocEntries = buildMergedTocEntries(previousSections, currentSections);

  const summary = tocEntries.reduce<ReviewDiffModel['summary']>(
    (accumulator, entry) => {
      accumulator[entry.status] += 1;
      return accumulator;
    },
    {
      unchanged: 0,
      modified: 0,
      added: 0,
      removed: 0,
    }
  );

  return {
    tocEntries,
    changedEntries: tocEntries.filter((entry) => entry.status !== 'unchanged'),
    summary,
  };
}
