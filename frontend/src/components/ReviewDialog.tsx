import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  Calendar,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  MessageSquare,
  Save,
  User,
  X,
  XCircle,
} from 'lucide-react';

import {
  buildReviewDiffModel,
  type ReviewDiffEntry,
  type ReviewSectionStatus,
} from '@/features/reviews/reviewDiff';
import {
  getPersistedReviewProgress,
  markReviewStarted,
  saveSectionSuggestion,
  setReviewDecisionReady,
  updateReviewProgress,
} from '@/features/reviews/reviewProgress';
import { persistReviewDocumentSession } from '@/features/reviews/reviewSession';
import {
  formatReviewSuggestions,
  parseReviewSuggestions,
} from '@/features/reviews/reviewSuggestions';
import { useFocusTrap } from '@/hooks/useAccessibility';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/dateUtils';
import { parseDocumentHtml } from '@/lib/documentRenderer';
import { reportRuntimeError } from '@/lib/runtimeReporter';
import { getUsableVersionContent } from '@/pages/document-detail/helpers/previewHelpers';
import type { AttachmentOutlineItem, PreApprovePolicy, ReviewRequest, Version } from '@/types';

interface ReviewDialogProps {
  review: ReviewRequest;
  onClose: () => void;
  onApprove: (comments?: string) => void;
  onReject: (comments: string) => void;
  isLoading: boolean;
}

type ReviewStage = 'overview' | 'guided' | 'complete' | 'feedback';
type SectionDisplayTone = ReviewSectionStatus | 'suggested';

const SECTION_TONE_META: Record<
  SectionDisplayTone,
  {
    label: string;
    pillClassName: string;
    cardClassName: string;
    bodyClassName: string;
  }
> = {
  unchanged: {
    label: 'Unchanged',
    pillClassName: 'bg-slate-100 text-slate-600',
    cardClassName: 'border-slate-200 bg-white',
    bodyClassName: 'review-section-body',
  },
  modified: {
    label: 'Modified',
    pillClassName: 'bg-amber-100 text-amber-700',
    cardClassName: 'border-amber-200 bg-amber-50/70',
    bodyClassName: 'review-section-body review-section-body--modified',
  },
  added: {
    label: 'Added',
    pillClassName: 'bg-emerald-100 text-emerald-700',
    cardClassName: 'border-emerald-200 bg-emerald-50/70',
    bodyClassName: 'review-section-body review-section-body--added',
  },
  removed: {
    label: 'Deleted',
    pillClassName: 'bg-rose-100 text-rose-700',
    cardClassName: 'border-rose-200 bg-rose-50/70',
    bodyClassName: 'review-section-body review-section-body--removed',
  },
  suggested: {
    label: 'Suggestion',
    pillClassName: 'bg-sky-100 text-sky-700',
    cardClassName: 'border-sky-200 bg-sky-50/80',
    bodyClassName: 'review-section-body review-section-body--suggested',
  },
};

function normalizeLabel(value: string | undefined): string {
  return (value || '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function getVersionLabel(version: Version | null | undefined, fallback: string): string {
  if (!version) {
    return fallback;
  }

  return `v${version.semantic_version || `${version.version_number}.0.0`}`;
}

function selectBaselineVersion(
  currentVersion: Version | null | undefined,
  versions: Version[] | undefined
): Version | null {
  if (!currentVersion || !versions?.length) {
    return null;
  }

  const currentCreatedAt = new Date(currentVersion.created_at).getTime();

  const olderVersions = versions
    .filter((version) => version.id !== currentVersion.id)
    .filter((version) => {
      if (version.version_number !== currentVersion.version_number) {
        return version.version_number < currentVersion.version_number;
      }

      return new Date(version.created_at).getTime() < currentCreatedAt;
    })
    .sort((left, right) => {
      if (right.version_number !== left.version_number) {
        return right.version_number - left.version_number;
      }

      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
    });

  if (olderVersions.length > 0) {
    return olderVersions[0];
  }

  return (
    versions
      .filter((version) => version.id !== currentVersion.id)
      .sort((left, right) => {
        if (right.version_number !== left.version_number) {
          return right.version_number - left.version_number;
        }

        return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
      })[0] || null
  );
}

function reportAndRethrow(scope: string, message: string, error: unknown): never {
  reportRuntimeError({
    scope,
    message,
    error,
  });
  throw error;
}

function TonePill({ tone, children }: { tone: SectionDisplayTone; children?: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${SECTION_TONE_META[tone].pillClassName}`}
    >
      {children || SECTION_TONE_META[tone].label}
    </span>
  );
}

function SectionReader({
  entry,
  tone,
  note,
}: {
  entry: ReviewDiffEntry;
  tone: SectionDisplayTone;
  note?: string;
}) {
  const sectionHtml =
    tone === 'removed'
      ? entry.previousHtml || entry.currentHtml || ''
      : entry.currentHtml || entry.previousHtml || '';

  return (
    <div className={`rounded-2xl border p-5 ${SECTION_TONE_META[tone].cardClassName}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
            {entry.title}
          </p>
          {entry.pageStart ? (
            <p className="mt-1 text-sm text-slate-500">Page {entry.pageStart}</p>
          ) : null}
        </div>
        <TonePill tone={tone} />
      </div>

      {note ? (
        <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
            Reviewer Suggestion
          </p>
          <p className="mt-2 whitespace-pre-wrap">{note}</p>
        </div>
      ) : null}

      <div className={`mt-4 rounded-2xl px-5 py-5 ${SECTION_TONE_META[tone].bodyClassName}`}>
        <div className="document-preview-content">{parseDocumentHtml(sectionHtml)}</div>
      </div>
    </div>
  );
}

function buildFeedbackEntries(
  entries: ReviewDiffEntry[],
  sectionSuggestions: Array<{ title: string; comment: string }>
) {
  return sectionSuggestions.map((sectionSuggestion, index) => {
    const matchingEntry =
      entries.find(
        (entry) => normalizeLabel(entry.title) === normalizeLabel(sectionSuggestion.title)
      ) ||
      entries.find((entry) =>
        normalizeLabel(entry.title).includes(normalizeLabel(sectionSuggestion.title))
      ) ||
      null;

    return {
      entry:
        matchingEntry ||
        ({
          id: `feedback-${index}`,
          title: sectionSuggestion.title,
          level: 1,
          status: 'modified',
          previousHtml: null,
          currentHtml: null,
          diffRows: [],
        } as ReviewDiffEntry),
      comment: sectionSuggestion.comment,
    };
  });
}

function buildOpenDocumentUrl(params: {
  documentId: number;
  reviewId: number;
  focusedEntryId?: string;
}) {
  const searchParams = new URLSearchParams();
  searchParams.set('review_session', String(params.reviewId));
  if (params.focusedEntryId) {
    searchParams.set('review_section', params.focusedEntryId);
  }

  return `/documents/${params.documentId}/fullscreen?${searchParams.toString()}`;
}

export default function ReviewDialog({
  review,
  onClose,
  onApprove,
  onReject,
  isLoading,
}: ReviewDialogProps) {
  const [generalComment, setGeneralComment] = useState('');
  const [action, setAction] = useState<'approve' | 'reject' | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [persistedProgress, setPersistedProgress] = useState(() =>
    getPersistedReviewProgress(review.id)
  );
  const titleId = useId();
  const commentsErrorId = useId();
  const commentsRef = useRef<HTMLTextAreaElement>(null);

  const { containerRef } = useFocusTrap(onClose);
  const isPendingReview = review.status === 'pending';
  const parsedFeedback = useMemo(
    () => parseReviewSuggestions(review.review_comments),
    [review.review_comments]
  );
  const initialStage: ReviewStage = isPendingReview ? 'overview' : 'feedback';
  const [stage, setStage] = useState<ReviewStage>(initialStage);

  const versionQuery = useQuery({
    queryKey: ['review-dialog', 'version', review.document_id, review.version_id ?? 'none'],
    queryFn: async () => {
      try {
        return await api.getVersion(review.document_id, review.version_id as number);
      } catch (error) {
        return reportAndRethrow('review.dialog', 'Failed to load review version details', error);
      }
    },
    enabled: Boolean(review.version_id && review.document_id),
  });

  const versionsQuery = useQuery({
    queryKey: ['review-dialog', 'versions', review.document_id],
    queryFn: async () => {
      try {
        return await api.getVersions(review.document_id);
      } catch (error) {
        return reportAndRethrow('review.dialog', 'Failed to load document version history', error);
      }
    },
    enabled: Boolean(review.version_id && review.document_id),
  });

  const attachmentsQuery = useQuery({
    queryKey: ['review-dialog', 'attachments', review.document_id],
    queryFn: async () => {
      try {
        return await api.getAttachments(review.document_id);
      } catch (error) {
        return reportAndRethrow('review.dialog', 'Failed to load document attachments', error);
      }
    },
    enabled: Boolean(review.document_id),
  });

  const selectedAttachment = useMemo(
    () =>
      attachmentsQuery.data?.find((attachment) => attachment.reader_html_status === 'ready') ||
      null,
    [attachmentsQuery.data]
  );

  const readerViewQuery = useQuery({
    queryKey: [
      'review-dialog',
      'reader-view',
      review.document_id,
      selectedAttachment?.id ?? 'none',
    ],
    queryFn: async () => {
      try {
        return await api.getAttachmentReaderView(review.document_id, selectedAttachment!.id);
      } catch (error) {
        return reportAndRethrow(
          'review.dialog',
          'Failed to load preview table of contents for review',
          error
        );
      }
    },
    enabled: Boolean(review.document_id && selectedAttachment?.id),
  });

  const policyQuery = useQuery({
    queryKey: ['review-dialog', 'policy', review.id],
    queryFn: async () => {
      try {
        return await api.getPreApprovePolicy(review.id);
      } catch (error) {
        return reportAndRethrow('review.dialog', 'Failed to load pre-approve policy', error);
      }
    },
    enabled: isPendingReview,
  });

  const baselineVersionCandidate = useMemo(
    () => selectBaselineVersion(versionQuery.data || null, versionsQuery.data?.items),
    [versionQuery.data, versionsQuery.data?.items]
  );

  const baselineVersionQuery = useQuery({
    queryKey: [
      'review-dialog',
      'baseline-version',
      review.document_id,
      baselineVersionCandidate?.id ?? 'none',
    ],
    queryFn: async () => {
      try {
        return await api.getVersion(review.document_id, baselineVersionCandidate!.id);
      } catch (error) {
        return reportAndRethrow(
          'review.dialog',
          'Failed to load previous version for review comparison',
          error
        );
      }
    },
    enabled: Boolean(review.document_id && baselineVersionCandidate?.id),
  });

  const version = versionQuery.data || null;
  const baselineVersion = baselineVersionQuery.data || baselineVersionCandidate || null;
  const preApprovePolicy: PreApprovePolicy | null = policyQuery.data || null;
  const policyError = policyQuery.isError
    ? 'Approval checks could not be loaded. Approval is temporarily disabled.'
    : null;

  const reviewDiff = useMemo(() => {
    const currentHtml = getUsableVersionContent(version?.content);
    if (!currentHtml) {
      return null;
    }

    return buildReviewDiffModel({
      previousHtml: getUsableVersionContent(baselineVersion?.content),
      currentHtml,
      tocItems: (readerViewQuery.data?.toc_items || []) as AttachmentOutlineItem[],
    });
  }, [baselineVersion?.content, readerViewQuery.data?.toc_items, version?.content]);

  const changedEntries = reviewDiff?.changedEntries || [];
  const currentVersionLabel = getVersionLabel(version, 'Submitted version');
  const baselineVersionLabel = getVersionLabel(baselineVersion, 'Previous version');
  const isDiffLoading =
    versionQuery.isLoading ||
    versionsQuery.isLoading ||
    baselineVersionQuery.isLoading ||
    (!!selectedAttachment?.id && readerViewQuery.isLoading);

  const sectionSuggestions = persistedProgress?.sectionSuggestions || {};
  const feedbackEntries = useMemo(
    () => buildFeedbackEntries(reviewDiff?.tocEntries || [], parsedFeedback.sectionSuggestions),
    [parsedFeedback.sectionSuggestions, reviewDiff?.tocEntries]
  );

  useEffect(() => {
    const nextProgress = getPersistedReviewProgress(review.id);
    setPersistedProgress(nextProgress);
    setGeneralComment(isPendingReview ? '' : parsedFeedback.generalComment);
    setAction(null);
    setShowConfirm(false);
    if (!isPendingReview) {
      setStage('feedback');
      return;
    }
    setStage(nextProgress?.decisionReady ? 'complete' : 'overview');
  }, [isPendingReview, parsedFeedback.generalComment, review.id]);

  useEffect(() => {
    if (!persistedProgress || changedEntries.length === 0 || !isPendingReview) {
      return;
    }

    const maxIndex = changedEntries.length - 1;
    if (persistedProgress.currentSectionIndex > maxIndex) {
      setPersistedProgress(
        updateReviewProgress(review.id, maxIndex, {
          decisionReady: persistedProgress.decisionReady,
          sectionSuggestions: persistedProgress.sectionSuggestions,
        })
      );
    }
  }, [changedEntries.length, isPendingReview, persistedProgress, review.id]);

  const activeEntryList = isPendingReview
    ? changedEntries
    : feedbackEntries.map((item) => item.entry);
  const activeIndex = useMemo(() => {
    if (activeEntryList.length === 0) {
      return 0;
    }

    return Math.max(
      0,
      Math.min(persistedProgress?.currentSectionIndex ?? 0, activeEntryList.length - 1)
    );
  }, [activeEntryList.length, persistedProgress?.currentSectionIndex]);
  const activeEntry = activeEntryList[activeIndex] || null;

  const activeFeedbackSuggestion = useMemo(() => {
    if (!activeEntry || isPendingReview) {
      return '';
    }

    return feedbackEntries.find((entry) => entry.entry.id === activeEntry.id)?.comment || '';
  }, [activeEntry, feedbackEntries, isPendingReview]);

  const canApprove =
    isPendingReview &&
    !policyQuery.isLoading &&
    !policyError &&
    preApprovePolicy?.can_approve === true;

  const hasStartedReview = persistedProgress !== null;
  const hasSectionSuggestions = Object.values(sectionSuggestions).some(
    (suggestion) => suggestion.trim().length > 0
  );
  const canSuggestChanges = generalComment.trim().length > 0 || hasSectionSuggestions;
  const rejectionFeedbackError = action === 'reject' && showConfirm && !canSuggestChanges;

  const persistSectionIndex = (index: number, decisionReady?: boolean) => {
    if (!isPendingReview) {
      return 0;
    }

    const nextProgress =
      persistedProgress === null
        ? markReviewStarted(review.id, index)
        : updateReviewProgress(review.id, index, {
            decisionReady: decisionReady ?? persistedProgress.decisionReady,
            sectionSuggestions: persistedProgress.sectionSuggestions,
          });
    setPersistedProgress(nextProgress);
    return nextProgress.currentSectionIndex;
  };

  const handleStartReview = () => {
    if (changedEntries.length === 0) {
      setStage('complete');
      setPersistedProgress(setReviewDecisionReady(review.id, true));
      return;
    }

    persistSectionIndex(activeIndex, false);
    setStage('guided');
  };

  const handleMoveBetweenSections = (direction: 1 | -1) => {
    const nextIndex = Math.max(0, Math.min(activeIndex + direction, activeEntryList.length - 1));
    persistSectionIndex(nextIndex, false);
  };

  const handleFinishGuidedReview = () => {
    const nextProgress = setReviewDecisionReady(review.id, true);
    setPersistedProgress(nextProgress);
    setStage('complete');
  };

  const handleSaveAndClose = () => {
    if (isPendingReview) {
      const decisionReady = stage === 'complete';
      const baseProgress = persistedProgress || markReviewStarted(review.id, activeIndex);
      setPersistedProgress(
        updateReviewProgress(review.id, activeIndex, {
          decisionReady,
          sectionSuggestions: baseProgress.sectionSuggestions,
        })
      );
    }

    onClose();
  };

  const handleSectionSuggestionChange = (value: string) => {
    if (!isPendingReview || !activeEntry) {
      return;
    }

    setPersistedProgress(saveSectionSuggestion(review.id, activeEntry.id, value));
  };

  const handleOpenDocumentInNewTab = () => {
    const sessionEntries = isPendingReview
      ? changedEntries.map((entry) => ({
          id: entry.id,
          title: entry.title,
          status: entry.status,
          anchorId: entry.anchorId,
        }))
      : feedbackEntries.map((item) => ({
          id: item.entry.id,
          title: item.entry.title,
          status: 'suggested' as const,
          anchorId: item.entry.anchorId,
        }));

    persistReviewDocumentSession({
      reviewId: review.id,
      documentId: review.document_id,
      mode: isPendingReview ? 'review' : 'suggestions',
      focusedEntryId: activeEntry?.id || sessionEntries[0]?.id,
      entries: sessionEntries,
      updatedAt: new Date().toISOString(),
    });

    const url = buildOpenDocumentUrl({
      documentId: review.document_id,
      reviewId: review.id,
      focusedEntryId: activeEntry?.id || sessionEntries[0]?.id,
    });
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleAction = (nextAction: 'approve' | 'reject') => {
    setAction(nextAction);
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    if (action === 'approve') {
      onApprove(generalComment.trim() || undefined);
      return;
    }

    if (!canSuggestChanges) {
      commentsRef.current?.focus();
      return;
    }

    const formattedSuggestions = formatReviewSuggestions({
      generalComment,
      sectionSuggestions: changedEntries
        .map((entry) => ({
          title: entry.title,
          comment: sectionSuggestions[entry.id] || '',
        }))
        .filter((entry) => entry.comment.trim().length > 0),
    });

    onReject(formattedSuggestions);
  };

  const showDecisionArea = isPendingReview && stage === 'complete';
  const showGuidedReview = isPendingReview && stage === 'guided' && activeEntry;
  const showFeedbackReview = !isPendingReview && activeEntry;
  const displayTone: SectionDisplayTone = !isPendingReview
    ? 'suggested'
    : activeEntry?.status || 'modified';

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close review dialog"
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="modal-content motion-enter-scale relative z-10 max-h-[92vh] w-full max-w-5xl overflow-hidden dark:bg-slate-900"
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h2
            id={titleId}
            className="text-lg font-semibold text-slate-900 font-display dark:text-slate-100"
          >
            {isPendingReview ? 'Review Document' : 'Review Feedback'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Close review dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="max-h-[calc(92vh-176px)] overflow-y-auto p-6">
          <div className="space-y-6">
            <div className="surface-muted rounded-2xl border border-slate-200 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <FileText className="mt-1 h-6 w-6 text-sky-600" />
                  <div>
                    <p className="text-xl font-semibold text-slate-900">
                      {review.document?.title || `Document #${review.document_id}`}
                    </p>
                    <p className="text-sm text-slate-500">{review.document?.document_number}</p>
                    <p className="mt-2 text-sm text-slate-600">
                      {version ? (
                        <>
                          Reviewing <span className="font-semibold">{currentVersionLabel}</span>
                          {baselineVersion ? (
                            <>
                              {' '}
                              against <span className="font-semibold">{baselineVersionLabel}</span>
                            </>
                          ) : null}
                          .
                        </>
                      ) : isDiffLoading ? (
                        'Preparing the review sections...'
                      ) : (
                        'This review is linked to the latest submitted version.'
                      )}
                    </p>
                  </div>
                </div>
                {isPendingReview ? (
                  <div className="flex flex-wrap gap-2">
                    <TonePill tone="modified">
                      {hasStartedReview ? 'In Progress' : 'Ready To Review'}
                    </TonePill>
                    {changedEntries.length > 0 ? (
                      <TonePill tone="unchanged">
                        {changedEntries.length} Changed Section
                        {changedEntries.length === 1 ? '' : 's'}
                      </TonePill>
                    ) : null}
                  </div>
                ) : review.status === 'rejected' ? (
                  <TonePill tone="suggested">Returned With Suggestions</TonePill>
                ) : null}
              </div>

              <div className="mt-4 grid gap-4 text-sm md:grid-cols-2">
                <div className="flex items-center gap-2 text-slate-600">
                  <User className="h-4 w-4" />
                  <span>
                    {isPendingReview ? 'Submitted by' : 'Reviewed by'}:{' '}
                    {isPendingReview
                      ? review.submitter?.full_name || 'Unknown'
                      : review.reviewer?.full_name || 'Unknown'}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <Calendar className="h-4 w-4" />
                  <span>
                    {isPendingReview ? 'Submitted' : 'Reviewed'}:{' '}
                    {formatDate(
                      isPendingReview
                        ? review.submitted_at
                        : review.reviewed_at || review.submitted_at
                    )}
                  </span>
                </div>
              </div>

              {review.message ? (
                <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <div className="flex items-start gap-2 text-slate-700">
                    <MessageSquare className="mt-0.5 h-4 w-4 text-slate-400" />
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        Submission Message
                      </p>
                      <p className="mt-1">{review.message}</p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
              <aside className="space-y-4">
                <div className="surface-card rounded-2xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      {isPendingReview ? 'Sections To Review' : 'Reviewer Notes'}
                    </p>
                    <span className="text-xs text-slate-400">
                      {activeEntryList.length} item{activeEntryList.length === 1 ? '' : 's'}
                    </span>
                  </div>

                  <div className="mt-4 space-y-2">
                    {activeEntryList.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                        {isDiffLoading
                          ? 'Preparing the review sections...'
                          : isPendingReview
                            ? 'No changed sections were detected for this submission.'
                            : 'No section-level suggestions were saved for this review.'}
                      </div>
                    ) : (
                      activeEntryList.map((entry, index) => {
                        const isActive =
                          (stage === 'guided' || stage === 'feedback') && index === activeIndex;
                        const tone = isPendingReview ? entry.status : 'suggested';

                        return (
                          <button
                            key={`${entry.id}-${index}`}
                            type="button"
                            disabled={isPendingReview && stage === 'overview'}
                            onClick={() => {
                              if (isPendingReview) {
                                persistSectionIndex(index, false);
                                setStage('guided');
                                return;
                              }
                              setPersistedProgress(
                                updateReviewProgress(review.id, index, {
                                  decisionReady: true,
                                  sectionSuggestions: persistedProgress?.sectionSuggestions,
                                })
                              );
                              setStage('feedback');
                            }}
                            className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                              SECTION_TONE_META[tone].cardClassName
                            } ${isActive ? 'ring-2 ring-sky-400 ring-offset-1' : ''} ${
                              isPendingReview && stage === 'overview'
                                ? 'cursor-default'
                                : 'hover:shadow-sm'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="truncate text-sm font-medium text-slate-900">
                                  {entry.title}
                                </p>
                                {entry.pageStart ? (
                                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                                    Page {entry.pageStart}
                                  </p>
                                ) : null}
                              </div>
                              <TonePill tone={tone} />
                            </div>
                          </button>
                        );
                      })
                    )}
                  </div>
                </div>
              </aside>

              <div className="space-y-4">
                {stage === 'overview' && isPendingReview ? (
                  <div className="surface-card rounded-2xl border border-slate-200 p-6">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Review Flow
                    </p>
                    <h3 className="mt-2 text-2xl font-semibold text-slate-900">
                      Read each changed section in the document flow
                    </h3>
                    <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
                      The review now stays close to the document itself. Each changed section is
                      shown as normal reading content with a quiet background tint so the reviewer
                      can stay in context without a noisy side-by-side diff.
                    </p>

                    <div className="mt-6 grid gap-3">
                      {changedEntries.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
                          No changed sections were detected. You can still finish the review and
                          leave final comments.
                        </div>
                      ) : (
                        changedEntries.map((entry, index) => (
                          <button
                            key={`${entry.id}-${entry.status}`}
                            type="button"
                            onClick={() => {
                              persistSectionIndex(index, false);
                              setStage('guided');
                            }}
                            className={`w-full rounded-2xl border px-4 py-4 text-left transition hover:shadow-sm ${SECTION_TONE_META[entry.status].cardClassName}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                                  Section {index + 1} of {changedEntries.length}
                                </p>
                                <p className="mt-1 text-base font-semibold text-slate-900">
                                  {entry.title}
                                </p>
                              </div>
                              <TonePill tone={entry.status} />
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                ) : null}

                {showGuidedReview && activeEntry ? (
                  <div className="space-y-4">
                    <div className="surface-card rounded-2xl border border-slate-200 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                            Reviewing Section {activeIndex + 1} of {activeEntryList.length}
                          </p>
                          <h3 className="mt-1 text-xl font-semibold text-slate-900">
                            {activeEntry.title}
                          </h3>
                        </div>
                        <button
                          type="button"
                          onClick={handleOpenDocumentInNewTab}
                          className="btn-ghost inline-flex items-center gap-2"
                        >
                          <ExternalLink className="h-4 w-4" />
                          Open This Section In New Tab
                        </button>
                      </div>
                    </div>

                    <SectionReader entry={activeEntry} tone={displayTone} />

                    <div className="surface-card rounded-2xl border border-slate-200 p-4">
                      <label
                        htmlFor="section-suggestion"
                        className="block text-sm font-medium text-slate-700"
                      >
                        Suggestion for editor
                      </label>
                      <p className="mt-1 text-sm text-slate-500">
                        Leave a section-specific note if you want this part changed before approval.
                      </p>
                      <textarea
                        id="section-suggestion"
                        value={activeEntry ? sectionSuggestions[activeEntry.id] || '' : ''}
                        onChange={(event) => handleSectionSuggestionChange(event.target.value)}
                        rows={4}
                        className="input-field mt-3"
                        placeholder="Example: expand this paragraph, clarify the date, or restore the removed line."
                      />
                    </div>
                  </div>
                ) : null}

                {showFeedbackReview && activeEntry ? (
                  <div className="space-y-4">
                    <div className="surface-card rounded-2xl border border-slate-200 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                            Feedback {activeIndex + 1} of {activeEntryList.length}
                          </p>
                          <h3 className="mt-1 text-xl font-semibold text-slate-900">
                            {activeEntry.title}
                          </h3>
                        </div>
                        <button
                          type="button"
                          onClick={handleOpenDocumentInNewTab}
                          className="btn-ghost inline-flex items-center gap-2"
                        >
                          <ExternalLink className="h-4 w-4" />
                          Open In Document
                        </button>
                      </div>
                    </div>

                    <SectionReader
                      entry={activeEntry}
                      tone="suggested"
                      note={activeFeedbackSuggestion}
                    />

                    {parsedFeedback.generalComment ? (
                      <div className="surface-card rounded-2xl border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                          General Feedback
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                          {parsedFeedback.generalComment}
                        </p>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {!isPendingReview && !showFeedbackReview && parsedFeedback.generalComment ? (
                  <div className="surface-card rounded-2xl border border-slate-200 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      General Feedback
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                      {parsedFeedback.generalComment}
                    </p>
                  </div>
                ) : null}

                {showDecisionArea ? (
                  <>
                    <div className="surface-card rounded-2xl border border-slate-200 p-6">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        Final Review
                      </p>
                      <h3 className="mt-2 text-2xl font-semibold text-slate-900">
                        Finish the review after reading all changed sections
                      </h3>
                      <p className="mt-3 text-sm leading-7 text-slate-600">
                        You can approve this version or send it back with section suggestions. Any
                        notes you wrote above will be saved into the review feedback and shown when
                        the editor opens the returned review.
                      </p>
                    </div>

                    <div className="surface-card rounded-2xl border border-slate-200 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                            Open The Full Document
                          </p>
                          <p className="mt-1 text-sm text-slate-600">
                            The document opens on the active section and keeps the same quiet color
                            highlights across the full page.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={handleOpenDocumentInNewTab}
                          className="btn-ghost inline-flex items-center gap-2"
                        >
                          <ExternalLink className="h-4 w-4" />
                          Open Document In New Tab
                        </button>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start gap-3">
                        <CheckCircle className="mt-0.5 h-4 w-4 text-sky-600" />
                        <div className="flex-1 space-y-3">
                          <div>
                            <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                              Approval Policy
                            </p>
                            {policyQuery.isLoading ? (
                              <div className="mt-2 flex items-center gap-2 text-sm text-slate-500">
                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-sky-600"></div>
                                Loading approval checks...
                              </div>
                            ) : policyError ? (
                              <p className="mt-2 text-sm text-rose-700">{policyError}</p>
                            ) : (
                              <>
                                {preApprovePolicy?.audience_summary ? (
                                  <p className="mt-2 text-sm text-slate-700">
                                    {preApprovePolicy.audience_summary}
                                  </p>
                                ) : null}
                                <ul className="mt-3 space-y-2 text-sm">
                                  {preApprovePolicy?.checks.map((check) => (
                                    <li
                                      key={check.id}
                                      className="rounded-xl border border-slate-200 bg-white px-3 py-2"
                                    >
                                      <div className="flex items-start gap-2">
                                        {check.passed ? (
                                          <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                                        ) : (
                                          <XCircle className="mt-0.5 h-4 w-4 text-rose-600" />
                                        )}
                                        <div>
                                          <p className="font-medium text-slate-800">
                                            {check.label}
                                          </p>
                                          {check.message ? (
                                            <p className="mt-1 text-slate-600">{check.message}</p>
                                          ) : null}
                                        </div>
                                      </div>
                                    </li>
                                  ))}
                                </ul>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="review-comments"
                        className="mb-2 block text-sm font-medium text-slate-700"
                      >
                        General review note
                      </label>
                      <textarea
                        ref={commentsRef}
                        id="review-comments"
                        value={generalComment}
                        onChange={(event) => setGeneralComment(event.target.value)}
                        rows={4}
                        className="input-field"
                        placeholder="Optional overall note for the submitter."
                        aria-invalid={rejectionFeedbackError}
                        aria-describedby={rejectionFeedbackError ? commentsErrorId : undefined}
                      />
                      {rejectionFeedbackError ? (
                        <p id={commentsErrorId} role="alert" className="mt-2 text-sm text-rose-600">
                          Add a general note or at least one section suggestion before sending the
                          review back.
                        </p>
                      ) : null}
                    </div>

                    {showConfirm ? (
                      <div
                        className={`rounded-2xl border p-4 ${
                          action === 'approve'
                            ? 'border-emerald-200 bg-emerald-50'
                            : 'border-sky-200 bg-sky-50'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <AlertTriangle
                            className={`h-5 w-5 ${
                              action === 'approve' ? 'text-emerald-600' : 'text-sky-600'
                            }`}
                          />
                          <div>
                            <p
                              className={`font-medium ${
                                action === 'approve' ? 'text-emerald-800' : 'text-sky-800'
                              }`}
                            >
                              {action === 'approve' ? 'Confirm Approval' : 'Confirm Suggestions'}
                            </p>
                            <p
                              className={`mt-1 text-sm ${
                                action === 'approve' ? 'text-emerald-700' : 'text-sky-700'
                              }`}
                            >
                              {action === 'approve'
                                ? canApprove
                                  ? 'This will approve the submitted version.'
                                  : 'Approval is blocked until every policy check passes.'
                                : 'This will return the review with your section suggestions for the editor.'}
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-950/70 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={onClose} disabled={isLoading} className="btn-ghost">
              Cancel
            </button>

            {isPendingReview ? (
              <button
                type="button"
                onClick={handleSaveAndClose}
                disabled={isLoading}
                className="btn-ghost inline-flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                Save & Come Back Later
              </button>
            ) : null}

            {stage === 'overview' && isPendingReview ? (
              <button
                type="button"
                onClick={handleStartReview}
                disabled={isLoading || isDiffLoading}
                className="btn-secondary"
              >
                {hasStartedReview ? 'Continue Review' : 'Start Review'}
              </button>
            ) : null}

            {showGuidedReview ? (
              <>
                <button
                  type="button"
                  onClick={() => handleMoveBetweenSections(-1)}
                  disabled={isLoading || activeIndex === 0}
                  className="btn-ghost inline-flex items-center gap-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous Section
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (activeIndex === activeEntryList.length - 1) {
                      handleFinishGuidedReview();
                      return;
                    }
                    handleMoveBetweenSections(1);
                  }}
                  disabled={isLoading}
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  {activeIndex === activeEntryList.length - 1 ? (
                    'Go To Final Review'
                  ) : (
                    <>
                      Next Section
                      <ChevronRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </>
            ) : null}

            {showDecisionArea ? (
              <button
                type="button"
                onClick={() => setStage('guided')}
                disabled={isLoading || activeEntryList.length === 0}
                className="btn-ghost"
              >
                Back To Sections
              </button>
            ) : null}
          </div>

          {showDecisionArea ? (
            <div className="flex flex-wrap items-center justify-end gap-3">
              {!showConfirm ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleAction('reject')}
                    disabled={isLoading}
                    className="flex items-center gap-2 rounded-full bg-sky-100 px-4 py-2 font-medium text-sky-700 transition hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <MessageSquare className="h-4 w-4" />
                    Suggest Changes
                  </button>
                  <button
                    type="button"
                    onClick={() => handleAction('approve')}
                    disabled={isLoading || !canApprove}
                    className="flex items-center gap-2 rounded-full bg-emerald-600 px-4 py-2 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Approve
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setShowConfirm(false)}
                    disabled={isLoading}
                    className="btn-ghost"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirm}
                    disabled={
                      isLoading ||
                      (action === 'approve' && !canApprove) ||
                      (action === 'reject' && !canSuggestChanges)
                    }
                    className={`flex items-center gap-2 rounded-full px-4 py-2 font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-50 ${
                      action === 'approve'
                        ? 'bg-emerald-600 hover:bg-emerald-700'
                        : 'bg-sky-600 hover:bg-sky-700'
                    }`}
                  >
                    {isLoading ? (
                      'Processing...'
                    ) : action === 'approve' ? (
                      <>
                        <CheckCircle className="h-4 w-4" />
                        Confirm Approval
                      </>
                    ) : (
                      <>
                        <MessageSquare className="h-4 w-4" />
                        Confirm Suggestions
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
