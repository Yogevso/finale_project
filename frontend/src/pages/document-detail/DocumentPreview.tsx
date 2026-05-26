import { useState, useEffect, useCallback, useMemo, useRef, type ReactNode } from 'react';
import { AlertTriangle, ArrowUpRight } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getDocument, getDomParser } from '@/env/dom';
import { api } from '@/lib/api';
import { useAttachmentDownload } from '@/hooks/useAttachmentDownload';
import { useDocumentCommentsQuery } from '@/hooks/useDocumentQueries';
import { useAuth } from '@/lib/auth';
import { getReviewDocumentSession } from '@/features/reviews/reviewSession';
import { queryKeys } from '@/lib/queryKeys';
import { reportRuntimeError } from '@/lib/runtimeReporter';
import type { CSSProperties } from 'react';
import type { ReadingWidth } from '@/lib/readingWidth';
import type { Attachment, Comment, FeedbackDetailResponse } from '@/types';
import {
  applyCommentHighlights,
  applyHighlights,
  clearCommentHighlights,
  clearHighlights,
  findSectionMatchInRoot,
  getUsableVersionContent,
  processHtmlIntoSections,
  resolveSectionPageStart,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers';
import { ContentEditChooserPopup } from '@/pages/document-detail/components/ContentEditChooserPopup';
import { DocumentCommentsSidebar } from '@/pages/document-detail/components/DocumentCommentsSidebar';
import { DocumentFeedbackSidebar } from '@/pages/document-detail/components/DocumentFeedbackSidebar';
import { PreviewCanvas } from '@/pages/document-detail/components/PreviewCanvas';
import { PreviewToolbar } from '@/pages/document-detail/components/PreviewToolbar';
import { SectionEditPopup } from '@/pages/document-detail/components/SectionEditPopup';
import { TocPanel } from '@/pages/document-detail/components/TocPanel';
import {
  useContentEditingFlow,
  type RemovedSection,
} from '@/pages/document-detail/hooks/useContentEditingFlow';
import { useInlineComments } from '@/pages/document-detail/hooks/useInlineComments';
import { usePreviewProgress } from '@/pages/document-detail/hooks/usePreviewProgress';
import { usePreviewShortcuts } from '@/pages/document-detail/hooks/usePreviewShortcuts';
import { usePreviewSource } from '@/pages/document-detail/hooks/usePreviewSource';
import { useReaderView } from '@/pages/document-detail/hooks/useReaderView';
import {
  DOCUMENT_FONT_SIZE_VALUES,
  getDocumentFontSize,
  getDocumentTheme,
  getDocumentThemeClassName,
  setDocumentFontSize,
  setDocumentTheme,
  type DocumentFontSize,
  type DocumentTheme,
} from '@/lib/documentReadingPreferences';

const WORDS_PER_MINUTE = 200;

function areTocSectionsEquivalent(left: TocSection[], right: TocSection[]): boolean {
  if (left.length !== right.length) {
    return false;
  }

  for (let index = 0; index < left.length; index += 1) {
    const leftSection = left[index];
    const rightSection = right[index];
    if (
      leftSection.id !== rightSection.id ||
      leftSection.text !== rightSection.text ||
      leftSection.level !== rightSection.level ||
      leftSection.index !== rightSection.index ||
      (leftSection.anchorId || '') !== (rightSection.anchorId || '')
    ) {
      return false;
    }
  }

  return true;
}

function estimateReadingTimeMinutes(html: string | null): number | null {
  if (!html) {
    return null;
  }

  const textContent = getDomParser().parseFromString(html, 'text/html').body.textContent ?? '';
  const wordCount = textContent.trim().split(/\s+/).filter(Boolean).length;

  if (wordCount === 0) {
    return null;
  }

  return Math.max(1, Math.ceil(wordCount / WORDS_PER_MINUTE));
}

function sortCommentsNewestFirst(left: Comment, right: Comment): number {
  const leftTime = new Date(left.created_at).getTime();
  const rightTime = new Date(right.created_at).getTime();

  if (Number.isNaN(leftTime) && Number.isNaN(rightTime)) {
    return right.id - left.id;
  }
  if (Number.isNaN(leftTime)) {
    return 1;
  }
  if (Number.isNaN(rightTime)) {
    return -1;
  }

  return rightTime - leftTime;
}

export function DocumentPreview({
  documentId,
  attachments,
  documentTitle,
  onScrollProgress,
  onReadingTimeChange,
  isEditor,
  isFullscreen = false,
  showCanvasTitle = true,
  sectionLinkBasePath,
  widthMode = 'reading',
  contentEditRequestToken = 0,
  hasPendingReview = false,
  onToggleFullscreen,
  highlightAnchor,
  reviewSessionId,
  reviewSectionId,
  onRemovedSectionsChange,
  actionsBar,
  isRevamp = false,
}: {
  documentId: number;
  attachments: Attachment[];
  documentTitle?: string;
  onScrollProgress?: (progress: number) => void;
  onReadingTimeChange?: (minutes: number | null) => void;
  isEditor?: boolean;
  isFullscreen?: boolean;
  showCanvasTitle?: boolean;
  sectionLinkBasePath: string;
  widthMode?: ReadingWidth;
  contentEditRequestToken?: number;
  hasPendingReview?: boolean;
  onToggleFullscreen?: () => void;
  highlightAnchor?: string;
  reviewSessionId?: number | null;
  reviewSectionId?: string;
  onRemovedSectionsChange?: (
    sections: RemovedSection[],
    restore: (s: RemovedSection) => void,
    clear: () => void
  ) => void;
  actionsBar?: ReactNode;
  isRevamp?: boolean;
}) {
  const { user } = useAuth();
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sections, setSections] = useState<TocSection[]>([]);
  const [tocCollapsed, setTocCollapsed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMatchCount, setSearchMatchCount] = useState(0);
  const [activeSearchMatchIndex, setActiveSearchMatchIndex] = useState(-1);
  const [fontSize, setFontSizeState] = useState<DocumentFontSize>(() => getDocumentFontSize());
  const [theme, setThemeState] = useState<DocumentTheme>(() => getDocumentTheme());
  const { downloadAttachment } = useAttachmentDownload(documentId);
  const previewPaneRef = useRef<HTMLDivElement>(null);
  const commentsSidebarRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [showResolvedComments, setShowResolvedComments] = useState(false);
  const [activeCommentThreadId, setActiveCommentThreadId] = useState<number | null>(null);
  const [submittingReplyThreadId, setSubmittingReplyThreadId] = useState<number | null>(null);
  const [sidebarMode, setSidebarMode] = useState<'comments' | 'feedback'>('comments');
  const {
    selectionPopup,
    commentPopup,
    commentText,
    isPrivateComment,
    isSubmittingComment,
    setCommentText,
    setIsPrivateComment,
    handleMouseUp,
    handleOpenCommentForm,
    handleSubmitComment,
    handleCloseCommentPopup,
  } = useInlineComments(documentId, reviewSessionId ?? null);
  const commentsQuery = useDocumentCommentsQuery(documentId, reviewSessionId ?? null, Boolean(user));
  const allCommentsQuery = useDocumentCommentsQuery(documentId, null, Boolean(user && reviewSessionId));

  const commentThreads = useMemo(() => {
    const scopedThreads = (commentsQuery.data || []).filter((comment) => comment.parent_id === null);
    if (!reviewSessionId) {
      return scopedThreads;
    }

    const reviewAndSharedThreads = (allCommentsQuery.data || [])
      .filter((comment) => comment.parent_id === null)
      .filter((comment) => comment.review_id === null || comment.review_id === reviewSessionId);

    const mergedThreads = new Map<number, Comment>();
    reviewAndSharedThreads.forEach((thread) => mergedThreads.set(thread.id, thread));
    scopedThreads.forEach((thread) => mergedThreads.set(thread.id, thread));

    return Array.from(mergedThreads.values()).sort(sortCommentsNewestFirst);
  }, [allCommentsQuery.data, commentsQuery.data, reviewSessionId]);

  const commentThreadsById = useMemo(
    () => new Map(commentThreads.map((thread) => [thread.id, thread])),
    [commentThreads],
  );

  const visibleCommentThreads = useMemo(
    () =>
      showResolvedComments
        ? commentThreads
        : commentThreads.filter((thread) => !thread.is_resolved),
    [commentThreads, showResolvedComments],
  );

  const canResolveThreads = Boolean(
    user && ['system_admin', 'admin', 'manager', 'editor'].includes(user.role),
  );

  const invalidateCommentThreads = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.comments.byDocument(documentId, reviewSessionId ?? null),
    });
    if (reviewSessionId) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.comments.byDocument(documentId, null),
      });
    }
  }, [documentId, queryClient, reviewSessionId]);

  const toggleCommentResolutionMutation = useMutation({
    mutationFn: ({ threadId, resolve }: { threadId: number; resolve: boolean }) =>
      api.updateComment(documentId, threadId, { is_resolved: resolve }),
    onSuccess: () => {
      invalidateCommentThreads();
    },
  });

  const addReplyMutation = useMutation({
    mutationFn: ({
      threadId,
      content,
      reviewId,
    }: {
      threadId: number;
      content: string;
      reviewId?: number;
    }) =>
      api.createComment(documentId, {
        content,
        parent_id: threadId,
        review_id: reviewId,
      }),
    onSuccess: () => {
      setSubmittingReplyThreadId(null);
      invalidateCommentThreads();
    },
    onError: () => {
      setSubmittingReplyThreadId(null);
    },
  });

  const scrollThreadIntoSidebarView = useCallback((threadId: number) => {
    const threadElement = commentsSidebarRef.current?.querySelector<HTMLElement>(
      `[data-thread-id="${threadId}"]`,
    );
    threadElement?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, []);

  const scrollToThreadHighlight = useCallback((threadId: number) => {
    const container = getDocument().getElementById('document-content-area');
    if (!container) {
      return;
    }
    const highlight = container.querySelector<HTMLElement>(
      `.doc-comment-highlight[data-comment-thread-id="${threadId}"]`,
    );
    if (!highlight) {
      return;
    }
    highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, []);

  const handleSelectCommentThread = useCallback(
    (threadId: number) => {
      setSidebarMode('comments');
      setActiveCommentThreadId(threadId);
      scrollThreadIntoSidebarView(threadId);
      scrollToThreadHighlight(threadId);
    },
    [scrollThreadIntoSidebarView, scrollToThreadHighlight],
  );

  const handleToggleCommentThreadResolved = useCallback(
    (threadId: number, resolve: boolean) => {
      toggleCommentResolutionMutation.mutate({ threadId, resolve });
      if (resolve && !showResolvedComments && activeCommentThreadId === threadId) {
        setActiveCommentThreadId(null);
      }
    },
    [activeCommentThreadId, showResolvedComments, toggleCommentResolutionMutation],
  );

  const handleSubmitCommentReply = useCallback(
    (threadId: number, content: string) => {
      const trimmed = content.trim();
      if (!trimmed) {
        return;
      }
      const thread = commentThreadsById.get(threadId);
      const replyReviewId = thread ? (thread.review_id ?? undefined) : reviewSessionId ?? undefined;
      setSubmittingReplyThreadId(threadId);
      addReplyMutation.mutate({ threadId, content: trimmed, reviewId: replyReviewId });
    },
    [addReplyMutation, commentThreadsById, reviewSessionId],
  );

  const commentsLoading = commentsQuery.isLoading || (Boolean(reviewSessionId) && allCommentsQuery.isLoading);
  const commentsError = commentsQuery.isError || (Boolean(reviewSessionId) && allCommentsQuery.isError);
  const feedbackQuery = useQuery({
    queryKey: ['documents', documentId, 'feedback'],
    queryFn: async () => {
      const response = await api.getAllFeedback({
        page: 1,
        per_page: 100,
        document_id: documentId,
      });
      return response.items;
    },
    enabled: Boolean(user) && sidebarMode === 'feedback',
  });
  const feedbackItems = useMemo<FeedbackDetailResponse[]>(
    () => feedbackQuery.data || [],
    [feedbackQuery.data],
  );

  const handleSetFontSize = useCallback((value: DocumentFontSize) => {
    setFontSizeState(value);
    setDocumentFontSize(value);
  }, []);

  const handleSetTheme = useCallback((value: DocumentTheme) => {
    setThemeState(value);
    setDocumentTheme(value);
  }, []);

  const processHtmlWithSections = useCallback((html: string) => {
    return processHtmlIntoSections(html).html;
  }, []);

  const {
    readerHtmlContent,
    readerStatus,
    readerWarnings,
    readerConfidence,
    readerError,
    isReaderLoading,
    readerCurrentPage,
    activeHeading,
    setReaderCurrentPage,
    setActiveHeading,
    navigateReaderToSection,
    handleRetryReaderView,
  } = useReaderView({
    documentId,
    selectedAttachment,
    sections,
    setSections,
    processHtmlWithSections,
  });

  const {
    previewSource,
    previewableAttachments,
    activeHtmlContent,
    showingReaderView,
    shouldRenderHtmlPreview,
    previewState,
  } = usePreviewSource({
    attachments,
    selectedAttachment,
    setSelectedAttachment,
    inlineContent: htmlContent,
    readerHtmlContent,
    readerStatus,
  });

  const inlineSections = useMemo(() => {
    if (previewSource !== 'inline' || !activeHtmlContent) {
      return null;
    }
    return processHtmlIntoSections(activeHtmlContent).sections;
  }, [activeHtmlContent, previewSource]);

  useEffect(() => {
    if (previewSource !== 'inline') {
      return;
    }

    if (!inlineSections) {
      if (sections.length > 0) {
        setSections([]);
      }
      return;
    }

    // Keep TOC locked to the currently rendered inline HTML.
    // This guards against stale reader-outline updates overriding edited content TOC.
    if (!areTocSectionsEquivalent(sections, inlineSections)) {
      setSections(inlineSections);
    }
  }, [inlineSections, previewSource, sections]);

  const contentStyle = useMemo(
    () =>
      ({
        '--doc-font-size': DOCUMENT_FONT_SIZE_VALUES[fontSize],
      }) as CSSProperties,
    [fontSize]
  );

  const focusSearchMatch = useCallback(
    (targetIndex: number, behavior: ScrollBehavior = 'smooth') => {
      const container = getDocument().getElementById('document-content-area');
      if (!container) {
        setSearchMatchCount(0);
        setActiveSearchMatchIndex(-1);
        return;
      }

      const matches = Array.from(container.querySelectorAll<HTMLElement>('mark.doc-highlight'));
      if (matches.length === 0) {
        setSearchMatchCount(0);
        setActiveSearchMatchIndex(-1);
        return;
      }

      const normalizedIndex = ((targetIndex % matches.length) + matches.length) % matches.length;
      matches.forEach((match, index) => {
        match.classList.toggle('doc-highlight--active', index === normalizedIndex);
      });
      matches[normalizedIndex]?.scrollIntoView({ behavior, block: 'center' });
      setSearchMatchCount(matches.length);
      setActiveSearchMatchIndex(normalizedIndex);
    },
    []
  );

  const handlePreviousSearchMatch = useCallback(() => {
    if (searchMatchCount === 0) {
      return;
    }
    focusSearchMatch(activeSearchMatchIndex - 1);
  }, [activeSearchMatchIndex, focusSearchMatch, searchMatchCount]);

  const handleNextSearchMatch = useCallback(() => {
    if (searchMatchCount === 0) {
      return;
    }
    focusSearchMatch(activeSearchMatchIndex + 1);
  }, [activeSearchMatchIndex, focusSearchMatch, searchMatchCount]);

  const applyProcessedHtml = useCallback(
    (html: string) => {
      const processed = processHtmlIntoSections(html);
      setHtmlContent(processed.html);

      if (processed.sections.length === 0) {
        setSections([]);
        return;
      }

      // Inline editing should always reflect the live HTML section order exactly.
      setSections(processed.sections);
    },
    []
  );

  const {
    showContentEditChooser,
    editingSection,
    handleCloseContentEditChooser,
    handleStartEditingSection,
    handleEditFullDocument,
    handleChooseEditSection,
    handleChooseAddSection,
    handleCloseSectionEdit,
    handleBackToChooser,
    handleSaveSection,
    handleDeleteSection,
    removedSections,
    handleRestoreSection,
    clearRemovedSections,
  } = useContentEditingFlow({
    documentId,
    isEditor,
    contentEditRequestToken,
    showingReaderView: selectedAttachment !== null,
    activeHtmlContent: htmlContent,
    isLoading,
    sections,
    applyProcessedHtml,
    onRequireInlineContent: () => setSelectedAttachment(null),
  });

  // Expose removed sections to parent
  useEffect(() => {
    onRemovedSectionsChange?.(removedSections, handleRestoreSection, clearRemovedSections);
  }, [removedSections, handleRestoreSection, clearRemovedSections, onRemovedSectionsChange]);

  const { previewScrollProgress, handleScroll } = usePreviewProgress({
    documentId,
    activeHtmlContent,
    selectedAttachmentId: selectedAttachment?.id ?? null,
    previewPaneRef,
    activeHeading,
    setActiveHeading,
    sections,
    readerCurrentPage,
    setReaderCurrentPage,
    onScrollProgress,
    hasUser: !!user,
  });

  useEffect(() => {
    if (activeCommentThreadId === null) {
      return;
    }
    if (!visibleCommentThreads.some((thread) => thread.id === activeCommentThreadId)) {
      setActiveCommentThreadId(null);
    }
  }, [activeCommentThreadId, visibleCommentThreads]);

  useEffect(() => {
    const container = getDocument().getElementById('document-content-area');
    if (!activeHtmlContent || !container || !user) {
      if (container) {
        clearCommentHighlights(container);
      }
      return;
    }

    applyCommentHighlights(
      container,
      visibleCommentThreads
        .filter((thread) => (thread.anchor_text || '').trim().length > 0)
        .map((thread) => ({
          threadId: thread.id,
          anchorText: thread.anchor_text || '',
        })),
    );

    return () => {
      clearCommentHighlights(container);
    };
  }, [activeHtmlContent, user, visibleCommentThreads]);

  useEffect(() => {
    const container = getDocument().getElementById('document-content-area');
    if (!container) {
      return;
    }

    container.querySelectorAll('.doc-comment-highlight--active').forEach((element) => {
      element.classList.remove('doc-comment-highlight--active');
    });

    if (activeCommentThreadId === null) {
      return;
    }

    container
      .querySelectorAll<HTMLElement>(
        `.doc-comment-highlight[data-comment-thread-id="${activeCommentThreadId}"]`,
      )
      .forEach((element) => {
        element.classList.add('doc-comment-highlight--active');
      });
  }, [activeCommentThreadId, activeHtmlContent, visibleCommentThreads]);

  useEffect(() => {
    const container = getDocument().getElementById('document-content-area');
    if (!container) {
      return;
    }

    const handleCommentHighlightClick = (event: Event) => {
      const target = event.target as HTMLElement | null;
      const highlight = target?.closest<HTMLElement>('.doc-comment-highlight');
      if (!highlight) {
        return;
      }

      const threadId = Number(highlight.getAttribute('data-comment-thread-id'));
      if (!Number.isFinite(threadId)) {
        return;
      }

      setSidebarMode('comments');
      setActiveCommentThreadId(threadId);
      scrollThreadIntoSidebarView(threadId);
    };

    container.addEventListener('click', handleCommentHighlightClick);

    return () => {
      container.removeEventListener('click', handleCommentHighlightClick);
    };
  }, [scrollThreadIntoSidebarView]);

  useEffect(() => {
    const container = getDocument().getElementById('document-content-area');
    if (!activeHtmlContent || !container) {
      return;
    }

    const handleNativeMouseUp = (event: MouseEvent) => {
      handleMouseUp(event);
    };

    container.addEventListener('mouseup', handleNativeMouseUp);

    return () => {
      container.removeEventListener('mouseup', handleNativeMouseUp);
    };
  }, [activeHtmlContent, handleMouseUp]);

  useEffect(() => {
    const container = getDocument().getElementById('document-content-area');
    if (!activeHtmlContent || !container) {
      setSearchMatchCount(0);
      setActiveSearchMatchIndex(-1);
      return;
    }

    applyHighlights(container, searchTerm);
    const matches = container.querySelectorAll('mark.doc-highlight');
    if (matches.length === 0) {
      setSearchMatchCount(0);
      setActiveSearchMatchIndex(-1);
      return;
    }

    focusSearchMatch(0, 'auto');
  }, [activeHtmlContent, focusSearchMatch, searchTerm]);

  // Highlight anchor text from URL (e.g. ?highlight=some+text from chat "View in document")
  useEffect(() => {
    if (!highlightAnchor || !activeHtmlContent || searchTerm) return;
    const container = getDocument().getElementById('document-content-area');
    if (!container) return;

    // Small delay to let the DOM render
    const timer = setTimeout(() => {
      applyHighlights(container, highlightAnchor);
      const firstMark = container.querySelector('mark.doc-highlight');
      if (firstMark) {
        firstMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Add a pulsing animation then clear after a few seconds
        container.querySelectorAll('mark.doc-highlight').forEach((m) => {
          (m as HTMLElement).style.background = '#fbbf24';
          (m as HTMLElement).style.transition = 'background 2s ease';
        });
        setTimeout(() => {
          container.querySelectorAll('mark.doc-highlight').forEach((m) => {
            (m as HTMLElement).style.background = '#fef08a';
          });
        }, 2000);
        // Clear the highlight marks after 6 seconds
        setTimeout(() => {
          clearHighlights(container);
        }, 6000);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [highlightAnchor, activeHtmlContent, searchTerm]);

  useEffect(() => {
    if (!reviewSessionId || !activeHtmlContent) {
      return;
    }

    const session = getReviewDocumentSession(reviewSessionId);
    const container = getDocument().getElementById('document-content-area');
    if (!session || !container) {
      return;
    }

    const root =
      (container.querySelector('.docx-document, .pptx-presentation') as HTMLElement | null) ||
      container;

    const clearReviewHighlights = () => {
      root.querySelectorAll<HTMLElement>('.document-review-highlight').forEach((element) => {
        element.classList.remove(
          'document-review-highlight',
          'document-review-highlight--added',
          'document-review-highlight--modified',
          'document-review-highlight--removed',
          'document-review-highlight--suggested',
          'document-review-highlight--focus'
        );
        element.removeAttribute('data-review-entry-id');
      });
    };

    const applyReviewHighlights = () => {
      clearReviewHighlights();

      const focusedEntryId = reviewSectionId || session.focusedEntryId;
      const focusTarget = { current: null as HTMLElement | null };

      session.entries.forEach((entry) => {
        const match = findSectionMatchInRoot(root, {
          anchorId: entry.anchorId,
          text: entry.title,
        });
        const targetElement = match?.topLevelElement || null;
        if (!targetElement) {
          return;
        }

        targetElement.classList.add(
          'document-review-highlight',
          `document-review-highlight--${entry.status}`
        );
        targetElement.setAttribute('data-review-entry-id', entry.id);

        if (entry.id === focusedEntryId) {
          targetElement.classList.add('document-review-highlight--focus');
          focusTarget.current = targetElement;
        }
      });

      if (focusTarget.current) {
        focusTarget.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    };

    const timer = window.setTimeout(applyReviewHighlights, 260);

    return () => {
      window.clearTimeout(timer);
      clearReviewHighlights();
    };
  }, [activeHtmlContent, reviewSectionId, reviewSessionId]);

  useEffect(() => {
    onReadingTimeChange?.(estimateReadingTimeMinutes(activeHtmlContent));
  }, [activeHtmlContent, onReadingTimeChange]);

  useEffect(() => {
    let cancelled = false;

    const loadInlineContent = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const versionsResponse = await api.getVersions(documentId);
        if (cancelled) {
          return;
        }
        const withContent = versionsResponse.items.filter((version) =>
          Boolean(getUsableVersionContent(version.content))
        );
        const latestVersion = withContent.sort(
          (left, right) =>
            new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
        )[0];
        const publishedVersion = withContent
          .filter((version) => version.is_published)
          .sort(
            (left, right) =>
              new Date(right.published_at || right.created_at).getTime() -
              new Date(left.published_at || left.created_at).getTime()
          )[0];
        let versionToShow = latestVersion || publishedVersion;

        if (!versionToShow && versionsResponse.items.length > 0) {
          const prioritizedIds = [
            ...new Set([
              ...versionsResponse.items
                .sort(
                  (left, right) =>
                    new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
                )
                .map((version) => version.id),
              ...versionsResponse.items
                .filter((version) => version.is_published)
                .sort(
                  (left, right) =>
                    new Date(right.published_at || right.created_at).getTime() -
                    new Date(left.published_at || left.created_at).getTime()
                )
                .map((version) => version.id),
            ]),
          ];

          for (const versionId of prioritizedIds) {
            const fullVersion = await api.getVersion(documentId, versionId);
            if (cancelled) {
              return;
            }
            if (getUsableVersionContent(fullVersion?.content)) {
              versionToShow = fullVersion;
              break;
            }
          }
        }

        if (cancelled) {
          return;
        }

        const versionContent = getUsableVersionContent(versionToShow?.content);
        if (versionContent) {
          const processed = processHtmlIntoSections(versionContent);
          setHtmlContent(processed.html);
          if (!selectedAttachment) {
            setSections(processed.sections);
          }
        } else {
          setHtmlContent(null);
          if (!selectedAttachment) {
            setSections([]);
          }
        }
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        reportRuntimeError({
          scope: 'preview.inline',
          message: 'Preview load failed',
          error: loadError,
        });
        setError('Failed to load preview');
        setHtmlContent(null);
        if (!selectedAttachment) {
          setSections([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadInlineContent();

    return () => {
      cancelled = true;
    };
  }, [documentId, selectedAttachment]);

  const tocSectionsForHtml = sections;

  const handleReaderTocClick = useCallback(
    (item: TocSection) => {
      navigateReaderToSection(item, 'smooth');
    },
    [navigateReaderToSection]
  );

  const activeSectionIndex = useMemo(() => {
    if (tocSectionsForHtml.length === 0) {
      return -1;
    }

    return tocSectionsForHtml.findIndex((item) => {
      const pageStart = resolveSectionPageStart(item);
      const anchorId = item.anchorId || `heading-${item.index}`;
      return activeHeading === anchorId || (!!pageStart && readerCurrentPage === pageStart);
    });
  }, [activeHeading, readerCurrentPage, tocSectionsForHtml]);

  const activeCurrentSection = useMemo(() => {
    if (!shouldRenderHtmlPreview || tocSectionsForHtml.length === 0 || activeSectionIndex < 0) {
      return null;
    }

    const currentSection = tocSectionsForHtml[activeSectionIndex];
    const h2Section = [...tocSectionsForHtml.slice(0, activeSectionIndex + 1)]
      .reverse()
      .find((item) => item.level === 2);

    return h2Section || currentSection || null;
  }, [activeSectionIndex, shouldRenderHtmlPreview, tocSectionsForHtml]);

  const showCurrentSectionIndicator =
    !!activeCurrentSection && previewScrollProgress > 6 && activeSectionIndex > 0;

  const navigateBetweenSections = useCallback(
    (direction: 1 | -1) => {
      if (tocSectionsForHtml.length === 0) {
        return;
      }

      const currentIndex = activeSectionIndex >= 0 ? activeSectionIndex : 0;
      const nextIndex = Math.max(
        0,
        Math.min(tocSectionsForHtml.length - 1, currentIndex + direction)
      );
      const targetSection = tocSectionsForHtml[nextIndex];
      if (!targetSection) {
        return;
      }

      handleReaderTocClick(targetSection);
    },
    [activeSectionIndex, handleReaderTocClick, tocSectionsForHtml]
  );

  usePreviewShortcuts({
    searchInputRef,
    editingSection,
    showContentEditChooser,
    handleCloseCommentPopup,
    handleCloseContentEditChooser,
    handleCloseSectionEdit,
    navigateBetweenSections,
    onToggleFullscreen,
  });

  if (previewState === 'NO_CONTENT') {
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">??</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No Content Yet</h3>
        <p className="text-slate-500">
          This document has no content. Add content using the editor or upload a file.
        </p>
      </div>
    );
  }

  if (previewState === 'DOWNLOAD_ONLY') {
    const firstAttachment = attachments[0] ?? null;

    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">??</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">
          Preview Not Available
        </h3>
        <p className="text-slate-500 mb-4">
          This attachment can be downloaded, but it cannot be previewed inline.
          <br />
          Download the original file to view it.
        </p>
        {firstAttachment && (
          <button
            type="button"
            onClick={() => {
              void downloadAttachment(firstAttachment);
            }}
            className="btn-primary inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Download {firstAttachment.filename}
          </button>
        )}
      </div>
    );
  }

  const documentPaperClass =
    widthMode === 'fluid'
      ? `document-preview-paper document-preview-paper-fluid ${getDocumentThemeClassName(theme)}`
      : `document-preview-paper ${getDocumentThemeClassName(theme)}`;
  const previewStageHeightClass = isRevamp
    ? isFullscreen
      ? 'h-[calc(100vh-13rem)] min-h-[34rem]'
      : 'h-[72vh] min-h-[32rem]'
    : '';
  const htmlLayoutClassName = isRevamp
    ? 'document-preview-html-layout document-preview-html-layout--revamp flex h-full flex-col md:flex-row'
    : 'document-preview-html-layout flex h-[70vh] flex-col md:flex-row';

  return (
    <div
      className={`document-preview-shell surface-card overflow-hidden ${
        isRevamp ? 'rounded-3xl border-slate-200' : 'rounded-2xl'
      } ${isRevamp ? 'document-preview-shell--revamp' : ''}`}
    >
      <PreviewToolbar
        previewableAttachments={previewableAttachments}
        selectedAttachment={selectedAttachment}
        onSelectAttachment={setSelectedAttachment}
        readerError={readerError}
        onRetryReaderView={handleRetryReaderView}
        fontSize={fontSize}
        onSetFontSize={handleSetFontSize}
        theme={theme}
        onSetTheme={handleSetTheme}
      />

      {hasPendingReview && isEditor && !showingReaderView && (
        <div
          className={`border-b border-amber-200/80 ${
            isRevamp
              ? 'bg-amber-50/90'
              : 'bg-gradient-to-r from-amber-50 via-amber-50 to-white'
          }`}
          role="status"
          aria-live="polite"
        >
          <div
            className={`flex gap-2 px-4 ${
              isRevamp
                ? 'items-center justify-between py-2.5'
                : 'flex-col py-3 sm:flex-row sm:items-center sm:justify-between'
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 inline-flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Pending review in progress
                </p>
                {!isRevamp && (
                  <p className="text-sm text-amber-900">
                    Draft saves are locked until the current review is resolved by an admin or
                    manager.
                  </p>
                )}
              </div>
            </div>
            <a
              href={`/reviews?document_id=${documentId}`}
              className="inline-flex items-center gap-1 self-start rounded-full border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-amber-800 transition hover:border-amber-400 hover:bg-amber-100/40 sm:self-auto"
            >
              Open Reviews
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      )}

      <div
        className={`document-current-section-indicator overflow-hidden border-b border-slate-200 bg-white transition-all duration-200 ${
          showCurrentSectionIndicator ? 'max-h-11 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        {activeCurrentSection && (
          <button
            type="button"
            onClick={() => handleReaderTocClick(activeCurrentSection)}
            className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm text-slate-600 hover:bg-blue-50 hover:text-blue-700"
            title="Current section (J/K)"
          >
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-600">
              Current section
            </span>
            <span className="flex-1 truncate font-medium text-slate-700">
              {activeCurrentSection.text}
            </span>
          </button>
        )}
      </div>

      <div
        className={`document-preview-stage relative ${previewStageHeightClass}`}
        style={isRevamp ? undefined : { minHeight: '600px' }}
      >
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-600">{error}</p>
            </div>
          </div>
        ) : previewState === 'LOADING' ||
          isLoading ||
          (selectedAttachment && isReaderLoading && !activeHtmlContent) ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              {selectedAttachment && (
                <p className="text-xs text-slate-500 mt-3">Preparing document preview...</p>
              )}
            </div>
          </div>
        ) : previewState === 'READY' && shouldRenderHtmlPreview ? (
          <div className={htmlLayoutClassName}>
            <TocPanel
              sections={tocSectionsForHtml}
              tocCollapsed={tocCollapsed}
              onToggleCollapsed={() => setTocCollapsed((previous) => !previous)}
              activeHeading={activeHeading}
              readerCurrentPage={readerCurrentPage}
              isEditor={isEditor}
              showingReaderView={showingReaderView}
              sectionLinkBasePath={sectionLinkBasePath}
              onSectionClick={handleReaderTocClick}
              onEditSection={handleStartEditingSection}
              onDeleteSection={handleDeleteSection}
              onAddSectionAfter={handleChooseAddSection}
              isRevamp={isRevamp}
            />

            <PreviewCanvas
              previewPaneRef={previewPaneRef}
              documentPaperClass={documentPaperClass}
              activeHtmlContent={activeHtmlContent}
              showingReaderView={showingReaderView}
              showDocumentTitle={showCanvasTitle}
              documentTitle={documentTitle}
              selectedAttachmentFilename={selectedAttachment?.filename}
              actionsBar={actionsBar}
              searchTerm={searchTerm}
              searchMatchCount={searchMatchCount}
              activeSearchMatchIndex={activeSearchMatchIndex}
              extractionWarnings={readerWarnings}
              readerConfidence={readerConfidence}
              onSearchTermChange={setSearchTerm}
              onPreviousSearchMatch={handlePreviousSearchMatch}
              onNextSearchMatch={handleNextSearchMatch}
              searchInputRef={searchInputRef}
              tocSectionsCount={tocSectionsForHtml.length}
              readerCurrentPage={readerCurrentPage}
              isEditor={isEditor}
              commentPopupTopOffset={isFullscreen ? 76 : 0}
              scrollProgress={previewScrollProgress}
              contentStyle={contentStyle}
              sectionLinkBasePath={sectionLinkBasePath}
              onScroll={handleScroll}
              hasUser={!!user}
              selectionPopup={selectionPopup}
              commentPopup={commentPopup}
              commentText={commentText}
              isPrivateComment={isPrivateComment}
              isSubmittingComment={isSubmittingComment}
              onOpenCommentForm={handleOpenCommentForm}
              onCloseCommentPopup={handleCloseCommentPopup}
              onCommentTextChange={setCommentText}
              onPrivateCommentChange={setIsPrivateComment}
              onSubmitComment={handleSubmitComment}
              isRevamp={isRevamp}
            />

            {user ? (
              <div ref={commentsSidebarRef} className="h-full w-full flex-shrink-0 md:w-auto">
                <div className="mb-2 inline-flex rounded-full border border-slate-200 bg-white p-1 text-xs font-semibold">
                  <button
                    type="button"
                    onClick={() => setSidebarMode('comments')}
                    className={`rounded-full px-3 py-1.5 transition ${
                      sidebarMode === 'comments'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Comments
                  </button>
                  <button
                    type="button"
                    onClick={() => setSidebarMode('feedback')}
                    className={`rounded-full px-3 py-1.5 transition ${
                      sidebarMode === 'feedback'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Feedback
                  </button>
                </div>

                {sidebarMode === 'comments' ? (
                  <DocumentCommentsSidebar
                    threads={commentThreads}
                    isLoading={commentsLoading}
                    isError={commentsError}
                    showResolved={showResolvedComments}
                    activeThreadId={activeCommentThreadId}
                    canResolveThreads={canResolveThreads}
                    resolveMutationPending={toggleCommentResolutionMutation.isPending}
                    submittingReplyThreadId={submittingReplyThreadId}
                    onToggleShowResolved={setShowResolvedComments}
                    onThreadSelect={handleSelectCommentThread}
                    onToggleThreadResolved={handleToggleCommentThreadResolved}
                    onSubmitReply={handleSubmitCommentReply}
                  />
                ) : (
                  <DocumentFeedbackSidebar
                    feedbackItems={feedbackItems}
                    isLoading={feedbackQuery.isLoading}
                    isError={feedbackQuery.isError}
                  />
                )}
              </div>
            ) : null}
          </div>
        ) : previewState === 'ERROR' && selectedAttachment && readerError ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-700 font-medium mb-1">Preview unavailable</p>
              <p className="text-sm text-rose-600">{readerError}</p>
            </div>
          </div>
        ) : null}
      </div>

      {selectedAttachment && (
        <div className="document-preview-downloads border-t border-slate-200 p-3 bg-slate-50 flex justify-between items-center">
          <span className="text-sm text-slate-600">
            {documentTitle || selectedAttachment.filename}
          </span>
          <button
            type="button"
            onClick={() => {
              void downloadAttachment(selectedAttachment);
            }}
            className="btn-primary text-sm"
          >
            Download Original
          </button>
        </div>
      )}

      {showContentEditChooser && (
        <ContentEditChooserPopup
          sections={tocSectionsForHtml}
          onClose={handleCloseContentEditChooser}
          onEditFullDocument={handleEditFullDocument}
          onEditSection={handleChooseEditSection}
          onAddSection={handleChooseAddSection}
        />
      )}

      {editingSection && (
        <SectionEditPopup
          key={`${editingSection.id}:${editingSection.editMode ?? 'edit'}`}
          documentId={documentId}
          section={editingSection}
          onClose={handleCloseSectionEdit}
          onBack={editingSection.fromChooser ? handleBackToChooser : undefined}
          onSave={handleSaveSection}
          saveDisabled={hasPendingReview}
          saveDisabledReason="This document currently has a pending review. Resolve it before creating a new draft."
          reviewsLinkTo={`/reviews?document_id=${documentId}`}
        />
      )}
    </div>
  );
}
