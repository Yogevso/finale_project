import { buildVersionDiffRows, type VersionDiffRow } from '@/lib/versionDiff';
import {
  mapOutlineItemsToSections,
  parsePageFromAnchorId,
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

function normalizeAnchorForDiff(anchorId: string | undefined): string | null {
  const normalized = (anchorId || '').trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (parsePageFromAnchorId(normalized) !== null) {
    return null;
  }
  if (/^heading-\d+(?:-\d+)?$/i.test(normalized)) {
    return null;
  }
  return normalized;
}

function parseSectionNumberPath(title: string | undefined): number[] | null {
  const normalized = (title || '').trim();
  const match = normalized.match(/^(\d+(?:\.\d+)*)/);
  if (!match) {
    return null;
  }

  const numbers = match[1]
    .split('.')
    .map((value) => Number.parseInt(value, 10))
    .filter((value) => Number.isFinite(value));
  return numbers.length > 0 ? numbers : null;
}

function buildOccurrenceAwareKeys(sections: TocSection[]): string[] {
  const counts = new Map<string, number>();

  return sections.map((section) => {
    const anchorKey = normalizeAnchorForDiff(section.anchorId);
    const sectionNumberPath = parseSectionNumberPath(section.text);
    const baseKey =
      (anchorKey && `anchor:${anchorKey}`) ||
      (sectionNumberPath && `section:${sectionNumberPath.join('.')}`) ||
      normalizeSectionTitle(section.text) ||
      `section-${section.index}`;
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

function normalizeTextTokens(value: string): string[] {
  const normalized = value
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!normalized) {
    return [];
  }

  return normalized.split(' ').filter(Boolean);
}

function stripHtmlText(value: string | null | undefined): string {
  return (value || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

function tokenSimilarityScore(left: string | null | undefined, right: string | null | undefined): number {
  const leftTokens = new Set(normalizeTextTokens(left || ''));
  const rightTokens = new Set(normalizeTextTokens(right || ''));

  if (leftTokens.size === 0 && rightTokens.size === 0) {
    return 1;
  }
  if (leftTokens.size === 0 || rightTokens.size === 0) {
    return 0;
  }

  let intersection = 0;
  leftTokens.forEach((token) => {
    if (rightTokens.has(token)) {
      intersection += 1;
    }
  });

  const union = leftTokens.size + rightTokens.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

function sectionPathEquals(leftTitle: string | undefined, rightTitle: string | undefined): boolean {
  const leftPath = parseSectionNumberPath(leftTitle);
  const rightPath = parseSectionNumberPath(rightTitle);
  if (!leftPath || !rightPath || leftPath.length !== rightPath.length) {
    return false;
  }

  return leftPath.every((value, index) => value === rightPath[index]);
}

function shouldTreatAsModified(
  removedEntry: ReviewDiffEntry,
  addedEntry: ReviewDiffEntry,
  options?: { indexDistance?: number }
): boolean {
  const levelDistance = Math.abs((removedEntry.level || 1) - (addedEntry.level || 1));
  if (levelDistance > 1) {
    return false;
  }

  const indexDistance = Math.max(0, options?.indexDistance ?? Number.POSITIVE_INFINITY);
  const titleScore = tokenSimilarityScore(removedEntry.title, addedEntry.title);
  const bodyScore = tokenSimilarityScore(
    stripHtmlText(removedEntry.previousHtml || removedEntry.currentHtml),
    stripHtmlText(addedEntry.currentHtml || addedEntry.previousHtml)
  );
  const sameSectionPath = sectionPathEquals(removedEntry.title, addedEntry.title);

  if (sameSectionPath && (titleScore >= 0.2 || bodyScore >= 0.05)) {
    return true;
  }

  // Prefer "modified" when we have strong textual evidence, and allow close-by title-renames.
  return (
    bodyScore >= 0.5 ||
    titleScore >= 0.82 ||
    (titleScore >= 0.55 && indexDistance <= 2) ||
    (titleScore >= 0.45 && bodyScore >= 0.15)
  );
}

function mergeReplacementEntries(
  removedEntry: ReviewDiffEntry,
  addedEntry: ReviewDiffEntry
): ReviewDiffEntry {
  const diffRows = buildVersionDiffRows(
    removedEntry.previousHtml || removedEntry.currentHtml || '',
    addedEntry.currentHtml || addedEntry.previousHtml || ''
  );
  const status: ReviewSectionStatus = diffRows.some((row) => row.status !== 'unchanged')
    ? 'modified'
    : 'unchanged';

  return {
    id: addedEntry.id || removedEntry.id,
    title: addedEntry.title || removedEntry.title,
    level: addedEntry.level || removedEntry.level,
    status,
    previousHtml: removedEntry.previousHtml || removedEntry.currentHtml || null,
    currentHtml: addedEntry.currentHtml || addedEntry.previousHtml || null,
    diffRows,
    anchorId: addedEntry.anchorId || removedEntry.anchorId,
    pageStart: addedEntry.pageStart || removedEntry.pageStart,
    pageEnd: addedEntry.pageEnd ?? removedEntry.pageEnd ?? null,
  };
}

function coalesceAdjacentReplacementPairs(entries: ReviewDiffEntry[]): ReviewDiffEntry[] {
  const mergedEntries: ReviewDiffEntry[] = [];

  for (let index = 0; index < entries.length; index += 1) {
    const currentEntry = entries[index];
    const nextEntry = entries[index + 1];

    if (
      currentEntry.status === 'removed' &&
      nextEntry?.status === 'added' &&
      shouldTreatAsModified(currentEntry, nextEntry, { indexDistance: 1 })
    ) {
      mergedEntries.push(mergeReplacementEntries(currentEntry, nextEntry));
      index += 1;
      continue;
    }

    if (
      currentEntry.status === 'added' &&
      nextEntry?.status === 'removed' &&
      shouldTreatAsModified(nextEntry, currentEntry, { indexDistance: 1 })
    ) {
      mergedEntries.push(mergeReplacementEntries(nextEntry, currentEntry));
      index += 1;
      continue;
    }

    mergedEntries.push(currentEntry);
  }

  return mergedEntries;
}

function coalesceNonAdjacentReplacementPairs(entries: ReviewDiffEntry[]): ReviewDiffEntry[] {
  const removedIndices = entries
    .map((entry, index) => (entry.status === 'removed' ? index : -1))
    .filter((index) => index >= 0);
  const addedIndices = entries
    .map((entry, index) => (entry.status === 'added' ? index : -1))
    .filter((index) => index >= 0);

  if (removedIndices.length === 0 || addedIndices.length === 0) {
    return entries;
  }

  const candidatePairs: Array<{
    removedIndex: number;
    addedIndex: number;
    indexDistance: number;
    confidence: number;
  }> = [];

  removedIndices.forEach((removedIndex) => {
    addedIndices.forEach((addedIndex) => {
      const removedEntry = entries[removedIndex];
      const addedEntry = entries[addedIndex];
      const indexDistance = Math.abs(removedIndex - addedIndex);
      const sameSectionPath = sectionPathEquals(removedEntry.title, addedEntry.title);

      if (!sameSectionPath || !shouldTreatAsModified(removedEntry, addedEntry, { indexDistance })) {
        return;
      }

      const titleScore = tokenSimilarityScore(removedEntry.title, addedEntry.title);
      const bodyScore = tokenSimilarityScore(
        stripHtmlText(removedEntry.previousHtml || removedEntry.currentHtml),
        stripHtmlText(addedEntry.currentHtml || addedEntry.previousHtml)
      );
      const confidence =
        bodyScore * 0.62 +
        titleScore * 0.3 +
        (sameSectionPath ? 0.25 : 0) -
        Math.min(indexDistance, 8) * 0.03;

      candidatePairs.push({
        removedIndex,
        addedIndex,
        indexDistance,
        confidence,
      });
    });
  });

  if (candidatePairs.length === 0) {
    return entries;
  }

  candidatePairs.sort((left, right) => {
    if (right.confidence !== left.confidence) {
      return right.confidence - left.confidence;
    }
    return left.indexDistance - right.indexDistance;
  });

  const usedRemoved = new Set<number>();
  const usedAdded = new Set<number>();
  const pairByIndex = new Map<number, number>();

  candidatePairs.forEach((pair) => {
    if (usedRemoved.has(pair.removedIndex) || usedAdded.has(pair.addedIndex)) {
      return;
    }
    usedRemoved.add(pair.removedIndex);
    usedAdded.add(pair.addedIndex);
    pairByIndex.set(pair.removedIndex, pair.addedIndex);
    pairByIndex.set(pair.addedIndex, pair.removedIndex);
  });

  if (pairByIndex.size === 0) {
    return entries;
  }

  const mergedEntries: ReviewDiffEntry[] = [];
  const consumed = new Set<number>();

  for (let index = 0; index < entries.length; index += 1) {
    if (consumed.has(index)) {
      continue;
    }

    const pairIndex = pairByIndex.get(index);
    if (pairIndex === undefined) {
      mergedEntries.push(entries[index]);
      continue;
    }

    if (consumed.has(pairIndex)) {
      consumed.add(index);
      continue;
    }

    if (index > pairIndex) {
      continue;
    }

    const leftEntry = entries[index];
    const rightEntry = entries[pairIndex];
    const mergedEntry =
      leftEntry.status === 'removed'
        ? mergeReplacementEntries(leftEntry, rightEntry)
        : mergeReplacementEntries(rightEntry, leftEntry);

    mergedEntries.push(mergedEntry);
    consumed.add(index);
    consumed.add(pairIndex);
  }

  return mergedEntries;
}

function coalesceReplacementPairs(entries: ReviewDiffEntry[]): ReviewDiffEntry[] {
  return coalesceNonAdjacentReplacementPairs(coalesceAdjacentReplacementPairs(entries));
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
    return tocItems.length > 0 ? mapOutlineItemsToSections(tocItems) : [];
  }

  // For review diffs we must preserve the exact live document structure/order from the version HTML.
  // Outline payloads can be stale and may duplicate or reorder sections.
  return processHtmlIntoSections(currentHtml).sections;
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
  const tocEntries = coalesceReplacementPairs(
    buildMergedTocEntries(previousSections, currentSections)
  );

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
