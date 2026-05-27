/**
 * CustomerDocumentPage - Document detail view for customer portal
 */
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { portalApi, type FeedbackItem, type FeedbackListResponse } from '../../lib/portalApi';
import { useAuth } from '@/lib/auth';
import { getDocument } from '@/env/dom';
import { parseDocumentHtml } from '@/lib/documentRenderer';
import { audienceSensitiveQueryOptions } from '@/lib/queryFreshness';
import {
  applyCommentHighlights,
  applyHighlights,
  clearCommentHighlights,
  clearHighlights,
  findSectionMatchInRoot,
  filterOutlineSectionsByHtml,
  mapOutlineItemsToSections,
  mergeTocSections,
  processHtmlIntoSections,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers';
import { DocumentCommentsSidebar } from '@/pages/document-detail/components/DocumentCommentsSidebar';
import { InlineCommentPopups } from '@/pages/document-detail/components/InlineCommentPopups';
import { PreviewToolbar } from '@/pages/document-detail/components/PreviewToolbar';
import { TocPanel } from '@/pages/document-detail/components/TocPanel';
import type {
  CommentPopupState,
  SelectionPopupState,
} from '@/pages/document-detail/hooks/useInlineComments';
import FeedbackForm from '../../components/FeedbackForm';
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
import {
  FileText,
  ArrowLeft,
  Paperclip,
  Download,
  Tag,
  Folder,
  Clock,
  CheckCircle,
  BookOpen,
  LifeBuoy,
} from 'lucide-react';
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth';
import NotFoundState from '@/components/NotFoundState';
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar';

const EMPTY_SELECTION_POPUP: SelectionPopupState = { show: false, x: 0, y: 0, text: '', anchorId: '' };
const EMPTY_COMMENT_POPUP: CommentPopupState = {
  show: false,
  x: 0,
  y: 0,
  text: '',
  anchorId: '',
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function escapeSelector(value: string): string {
  return value.replace(/([ #;&,.+*~':"!^$[\]()=>|/@])/g, '\\$1');
}

function resolveAnchorId(selection: Selection): string {
  if (selection.rangeCount === 0) {
    return 'document-content-area';
  }

  const range = selection.getRangeAt(0);
  const node = range.commonAncestorContainer;
  const baseElement = (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement) as
    | HTMLElement
    | null;

  if (!baseElement) {
    return 'document-content-area';
  }

  const contentRoot = baseElement.closest<HTMLElement>('#document-content-area');
  if (!contentRoot) {
    return 'document-content-area';
  }

  const directHeading = baseElement.closest<HTMLElement>('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]');
  if (directHeading?.id) {
    return directHeading.id;
  }

  const headings = Array.from(
    contentRoot.querySelectorAll<HTMLElement>('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]'),
  );
  const nodeType = baseElement.ownerDocument.defaultView?.Node ?? Node;
  let fallbackHeadingId: string | null = null;

  for (const heading of headings) {
    if (heading === baseElement || heading.contains(baseElement)) {
      fallbackHeadingId = heading.id;
      break;
    }
    const relation = heading.compareDocumentPosition(baseElement);
    if (relation & nodeType.DOCUMENT_POSITION_FOLLOWING) {
      fallbackHeadingId = heading.id;
      continue;
    }
    if (relation & nodeType.DOCUMENT_POSITION_PRECEDING) {
      break;
    }
  }

  if (fallbackHeadingId) {
    return fallbackHeadingId;
  }

  return headings[0]?.id || 'document-content-area';
}

export default function CustomerDocumentPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [submittedFeedback, setSubmittedFeedback] = useState<FeedbackItem | null>(null);
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'));
  const [fontSize, setFontSizeState] = useState<DocumentFontSize>(() => getDocumentFontSize());
  const [theme, setThemeState] = useState<DocumentTheme>(() => getDocumentTheme());
  const [tocCollapsed, setTocCollapsed] = useState(false);
  const [activeHeading, setActiveHeading] = useState<string | null>(null);
  const [selectionPopup, setSelectionPopup] = useState<SelectionPopupState>(EMPTY_SELECTION_POPUP);
  const [commentPopup, setCommentPopup] = useState<CommentPopupState>(EMPTY_COMMENT_POPUP);
  const [commentText, setCommentText] = useState('');
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [showResolvedComments, setShowResolvedComments] = useState(false);
  const [activeCommentThreadId, setActiveCommentThreadId] = useState<number | null>(null);
  const [submittingReplyThreadId, setSubmittingReplyThreadId] = useState<number | null>(null);
  const { isCustomer, user } = useAuth();
  const contentRef = useRef<HTMLDivElement | null>(null);
  const commentsSidebarRef = useRef<HTMLDivElement | null>(null);
  const lastSavedProgress = useRef<number>(0);
  const rafId = useRef<number | null>(null);
  const isFullscreen = location.search.includes('fullscreen=1');
  const highlightText = useMemo(
    () => new URLSearchParams(location.search).get('highlight')?.trim() ?? '',
    [location.search]
  );

  const {
    data: document,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['portal', 'document', id],
    queryFn: () => portalApi.getDocument(Number(id)),
    enabled: !!id,
    ...audienceSensitiveQueryOptions,
  });
  const commentsQuery = useQuery({
    queryKey: ['portal', 'document', id, 'comments'],
    queryFn: () => portalApi.getDocumentComments(Number(id)),
    enabled: Boolean(id && user),
  });

  const commentThreads = useMemo(
    () => (commentsQuery.data || []).filter((comment) => comment.parent_id === null),
    [commentsQuery.data],
  );
  const visibleCommentThreads = useMemo(
    () =>
      showResolvedComments
        ? commentThreads
        : commentThreads.filter((thread) => !thread.is_resolved),
    [commentThreads, showResolvedComments],
  );
  const processedPreview = useMemo(
    () => processHtmlIntoSections(document?.content ?? ''),
    [document?.content]
  );
  const renderedContent = useMemo(
    () => parseDocumentHtml(processedPreview.html),
    [processedPreview.html]
  );
  const tocSections = useMemo(() => {
    const htmlSections = processedPreview.sections;
    const outlineSections = mapOutlineItemsToSections(document?.toc_items || []);
    if (outlineSections.length === 0) {
      return htmlSections;
    }

    const filteredOutlineSections = filterOutlineSectionsByHtml(
      outlineSections,
      processedPreview.html
    );
    if (filteredOutlineSections.length === 0) {
      return htmlSections;
    }

    return mergeTocSections(filteredOutlineSections, htmlSections);
  }, [document?.toc_items, processedPreview.html, processedPreview.sections]);
  const sectionLinkBasePath = isFullscreen
    ? `/portal/documents/${id}?fullscreen=1`
    : `/portal/documents/${id}`;
  const contentStyle = useMemo(
    () =>
      ({
        '--doc-font-size': DOCUMENT_FONT_SIZE_VALUES[fontSize],
      }) as CSSProperties,
    [fontSize]
  );
  const documentPaperClass = useMemo(
    () =>
      `${contentWidth === 'fluid' ? 'document-preview-paper document-preview-paper-fluid' : 'document-preview-paper'} ${getDocumentThemeClassName(theme)}`,
    [contentWidth, theme]
  );

  const { data: relatedDocs } = useQuery({
    queryKey: ['portal', 'document', id, 'related'],
    queryFn: () => portalApi.getRelatedDocuments(Number(id)),
    enabled: !!id,
    ...audienceSensitiveQueryOptions,
  });

  const closeCommentPopup = useCallback(() => {
    setSelectionPopup(EMPTY_SELECTION_POPUP);
    setCommentPopup(EMPTY_COMMENT_POPUP);
    setCommentText('');
    setIsSubmittingComment(false);
    window.getSelection()?.removeAllRanges();
  }, []);

  const invalidateComments = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['portal', 'document', id, 'comments'] });
  }, [id, queryClient]);

  const handleSetFontSize = useCallback((value: DocumentFontSize) => {
    setFontSizeState(value);
    setDocumentFontSize(value);
  }, []);

  const handleSetTheme = useCallback((value: DocumentTheme) => {
    setThemeState(value);
    setDocumentTheme(value);
  }, []);

  const feedbackMutation = useMutation({
    mutationFn: (data: {
      feedback_type: 'question' | 'suggestion' | 'issue' | 'other';
      content: string;
      anchor_text?: string;
    }) =>
      portalApi.submitFeedback({
        document_id: Number(id),
        ...data,
      }),
    onMutate: async (data) => {
      const optimisticFeedbackId = -Date.now();
      const nowIso = new Date().toISOString();
      const optimisticFeedback: FeedbackItem = {
        id: optimisticFeedbackId,
        document_id: Number(id),
        document_title: document?.title || 'Current document',
        ticket_id: null,
        feedback_type: data.feedback_type,
        content: data.content,
        anchor_text: data.anchor_text ?? null,
        status: 'pending',
        created_at: nowIso,
        updated_at: nowIso,
      };
      setSubmittedFeedback(optimisticFeedback);

      const previousFeedbackQueries = queryClient.getQueriesData<FeedbackListResponse>({
        queryKey: ['portal', 'feedback'],
      });

      previousFeedbackQueries.forEach(([queryKey, previous]) => {
        if (!previous) return;

        const filters =
          Array.isArray(queryKey) && typeof queryKey[2] === 'object' && queryKey[2] !== null
            ? (queryKey[2] as { status?: 'pending' | 'responded' | 'closed' })
            : undefined;

        if (filters?.status && filters.status !== 'pending') {
          return;
        }

        queryClient.setQueryData<FeedbackListResponse>(queryKey, {
          ...previous,
          items: [optimisticFeedback, ...previous.items],
          total: previous.total + 1,
        });
      });

      return { optimisticFeedbackId, previousFeedbackQueries };
    },
    onError: (_error, _variables, context) => {
      setSubmittedFeedback(null);
      context?.previousFeedbackQueries.forEach(([queryKey, previous]) => {
        queryClient.setQueryData(queryKey, previous);
      });
    },
    onSuccess: (createdFeedback, _variables, context) => {
      setSubmittedFeedback(createdFeedback);
      queryClient.setQueriesData<FeedbackListResponse>(
        { queryKey: ['portal', 'feedback'] },
        (current) => {
          if (!current) return current;
          return {
            ...current,
            items: current.items.map((item) =>
              item.id === context?.optimisticFeedbackId ? createdFeedback : item
            ),
          };
        }
      );
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['portal', 'feedback'] });
    },
  });

  const createCommentMutation = useMutation({
    mutationFn: (data: { content: string; anchor_text: string; anchor_id: string }) =>
      portalApi.createDocumentComment(Number(id), data),
    onSuccess: () => {
      closeCommentPopup();
      invalidateComments();
    },
    onError: () => {
      setIsSubmittingComment(false);
    },
  });

  const toggleCommentResolutionMutation = useMutation({
    mutationFn: ({ commentId, resolve }: { commentId: number; resolve: boolean }) =>
      portalApi.updateDocumentComment(Number(id), commentId, { is_resolved: resolve }),
    onSuccess: () => {
      invalidateComments();
    },
  });

  const addReplyMutation = useMutation({
    mutationFn: ({ threadId, content }: { threadId: number; content: string }) =>
      portalApi.createDocumentComment(Number(id), { content, parent_id: threadId }),
    onSuccess: () => {
      setSubmittingReplyThreadId(null);
      invalidateComments();
    },
    onError: () => {
      setSubmittingReplyThreadId(null);
    },
  });

  const updateProgressMutation = useMutation({
    mutationFn: (percent: number) => portalApi.updateReadingProgress(Number(id), percent),
  });

  const handleSelectionMouseUp = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if ((event.target as HTMLElement).closest('.inline-comment-popup')) {
        return;
      }

      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        if (!commentPopup.show) {
          setSelectionPopup(EMPTY_SELECTION_POPUP);
        }
        return;
      }

      const selectedText = selection.toString().trim();
      if (selectedText.length < 3) {
        setSelectionPopup(EMPTY_SELECTION_POPUP);
        return;
      }

      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setSelectionPopup({
        show: true,
        x: rect.left + rect.width / 2,
        y: rect.top - 10,
        text: selectedText,
        anchorId: resolveAnchorId(selection),
      });
    },
    [commentPopup.show]
  );

  const handleOpenCommentForm = useCallback(() => {
    if (!selectionPopup.text) {
      return;
    }

    setCommentPopup({
      show: true,
      x: selectionPopup.x,
      y: selectionPopup.y + 60,
      text: selectionPopup.text,
      anchorId: selectionPopup.anchorId || 'document-content-area',
    });
    setSelectionPopup(EMPTY_SELECTION_POPUP);
  }, [selectionPopup]);

  const handleSubmitComment = useCallback(() => {
    const trimmed = commentText.trim();
    if (!trimmed || !commentPopup.text) {
      return;
    }
    setIsSubmittingComment(true);
    createCommentMutation.mutate({
      content: trimmed,
      anchor_text: commentPopup.text,
      anchor_id: commentPopup.anchorId || 'document-content-area',
    });
  }, [commentPopup.anchorId, commentPopup.text, commentText, createCommentMutation]);

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
      setActiveCommentThreadId(threadId);
      scrollThreadIntoSidebarView(threadId);
      scrollToThreadHighlight(threadId);
    },
    [scrollThreadIntoSidebarView, scrollToThreadHighlight],
  );

  const handleToggleCommentThreadResolved = useCallback(
    (threadId: number, resolve: boolean) => {
      toggleCommentResolutionMutation.mutate({ commentId: threadId, resolve });
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
      setSubmittingReplyThreadId(threadId);
      addReplyMutation.mutate({
        threadId,
        content: trimmed,
      });
    },
    [addReplyMutation],
  );

  useEffect(() => {
    if (activeCommentThreadId === null) {
      return;
    }
    if (!visibleCommentThreads.some((thread) => thread.id === activeCommentThreadId)) {
      setActiveCommentThreadId(null);
    }
  }, [activeCommentThreadId, visibleCommentThreads]);

  useEffect(() => {
    const container = contentRef.current;
    if (!container) {
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
  }, [renderedContent, visibleCommentThreads]);

  useEffect(() => {
    const container = contentRef.current;
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
  }, [activeCommentThreadId, renderedContent, visibleCommentThreads]);

  useEffect(() => {
    const container = contentRef.current;
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

      setActiveCommentThreadId(threadId);
      scrollThreadIntoSidebarView(threadId);
    };

    container.addEventListener('click', handleCommentHighlightClick);
    return () => {
      container.removeEventListener('click', handleCommentHighlightClick);
    };
  }, [scrollThreadIntoSidebarView]);

  const computeAndSaveProgress = useCallback(() => {
    if (!isCustomer || !contentRef.current || !id) {
      return;
    }

    const element = contentRef.current;
    const scrollY = window.scrollY;
    const elementTop = element.getBoundingClientRect().top + scrollY;
    const elementHeight = element.scrollHeight;
    const viewportHeight = window.innerHeight;
    const end = elementTop + elementHeight - viewportHeight;

    let progress = 0;
    if (end <= elementTop) {
      progress = 100;
    } else if (scrollY <= elementTop) {
      progress = 0;
    } else if (scrollY >= end) {
      progress = 100;
    } else {
      progress = Math.round(((scrollY - elementTop) / (end - elementTop)) * 100);
    }

    progress = Math.max(0, Math.min(100, progress));
    if (progress <= lastSavedProgress.current) {
      // Continue updating the active TOC item even when progress doesn't advance.
    } else {
      const currentMilestone = Math.floor(progress / 10) * 10;
      const savedMilestone = Math.floor(lastSavedProgress.current / 10) * 10;
      if (currentMilestone > savedMilestone && progress > lastSavedProgress.current) {
        lastSavedProgress.current = progress;
        updateProgressMutation.mutate(progress);
      }
    }

    const headings = Array.from(
      element.querySelectorAll<HTMLElement>('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]')
    );
    if (headings.length === 0) {
      setActiveHeading(null);
      return;
    }

    const viewportOffset = isFullscreen ? 140 : 180;
    let nextActiveHeading: string | null = null;
    headings.forEach((heading) => {
      if (heading.getBoundingClientRect().top <= viewportOffset) {
        nextActiveHeading = heading.id;
      }
    });

    if (!nextActiveHeading) {
      nextActiveHeading = headings[0]?.id ?? null;
    }

    setActiveHeading(nextActiveHeading);
  }, [id, isCustomer, isFullscreen, updateProgressMutation]);

  useEffect(() => {
    if (!isCustomer || !id) {
      return;
    }

    const handleScroll = () => {
      if (rafId.current !== null) {
        return;
      }
      rafId.current = window.requestAnimationFrame(() => {
        rafId.current = null;
        computeAndSaveProgress();
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (rafId.current !== null) {
        window.cancelAnimationFrame(rafId.current);
        rafId.current = null;
      }
    };
  }, [computeAndSaveProgress, id, isCustomer]);

  useEffect(() => {
    const container = contentRef.current;
    if (!container) {
      return;
    }

    clearHighlights(container);
    if (!highlightText) {
      return;
    }

    let clearTimer: number | null = null;
    const applyTimer = window.setTimeout(() => {
      applyHighlights(container, highlightText);
      const firstHighlight = container.querySelector<HTMLElement>('mark.doc-highlight');
      if (firstHighlight) {
        firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
        clearTimer = window.setTimeout(() => {
          clearHighlights(container);
        }, 6000);
      }
    }, 250);

    return () => {
      window.clearTimeout(applyTimer);
      if (clearTimer !== null) {
        window.clearTimeout(clearTimer);
      }
      clearHighlights(container);
    };
  }, [highlightText, renderedContent]);

  const handleSectionClick = useCallback(
    (section: TocSection) => {
      const anchorId = section.anchorId || `heading-${section.index}`;
      const container = contentRef.current;
      if (!container) {
        return;
      }

      const byAnchor =
        container.querySelector<HTMLElement>(`#${escapeSelector(anchorId)}`) ??
        container.ownerDocument.getElementById(anchorId);
      const matched =
        byAnchor && container.contains(byAnchor)
          ? byAnchor
          : (findSectionMatchInRoot(container, section)?.element ?? null);
      const fallbackHeading =
        matched ??
        Array.from(
          container.querySelectorAll<HTMLElement>('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]')
        )[section.index] ??
        null;

      if (!fallbackHeading) {
        return;
      }

      const offset = isFullscreen ? 96 : 132;
      const targetTop = fallbackHeading.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
      setActiveHeading(fallbackHeading.id || anchorId);
    },
    [isFullscreen]
  );

  const applyWidth = (value: ReadingWidth) => {
    setContentWidth(value);
    setReadingWidth(value);
  };

  if (isLoading) {
    return (
      <div className="content-shell flex animate-fade-in justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="content-shell animate-fade-in py-12">
        <NotFoundState
          title="Document Not Found"
          description="This document may not exist or you don't have access to view it."
          icon={<FileText className="h-12 w-12 text-slate-300 dark:text-slate-600" />}
          action={
            <Link
              to="/portal/documents"
              className="btn-secondary table-action-btn inline-flex items-center gap-2"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Documents
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div
      className={`${isFullscreen ? 'min-h-screen bg-white py-6 dark:bg-slate-950' : 'page-stack'} animate-fade-in`}
    >
      <FullscreenTopBar
        isFullscreen={isFullscreen}
        documentTitle={document.title}
        contentWidth={contentWidth}
        onExitFullscreen={() => navigate(`/portal/documents/${id}`)}
        onSetReadingWidth={() => applyWidth('reading')}
        onSetFluidWidth={() => applyWidth('fluid')}
        wrapperClassName="mx-6 rounded-2xl px-4 md:mx-10 lg:mx-16"
      />

      <div
        className={`space-y-6 ${contentWidth === 'reading' ? 'reading-mode' : ''} ${isFullscreen ? `w-full ${contentWidth === 'reading' ? 'mx-auto max-w-5xl' : 'max-w-none'} px-6 md:px-10 lg:px-16` : ''}`}
      >
        <div className="flex items-center justify-between">
          <Link
            to="/portal/documents"
            className="btn-ghost table-action-btn inline-flex items-center gap-2"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Documents
          </Link>
          {!isFullscreen && (
            <button
              type="button"
              onClick={() => navigate(`/portal/documents/${id}?fullscreen=1`)}
              className="btn-ghost table-action-btn"
            >
              Fullscreen
            </button>
          )}
        </div>

        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 p-6 dark:border-slate-800">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="page-title text-slate-900 dark:text-slate-100">{document.title}</h1>
                {document.description && (
                  <p className="body-copy mt-2 dark:text-slate-300">{document.description}</p>
                )}
              </div>
              <span className="pill border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200">
                v{document.version}
              </span>
            </div>

            <div className="helper-copy mt-4 flex flex-wrap gap-4 dark:text-slate-400">
              {document.category && (
                <span className="inline-flex items-center">
                  <Folder className="mr-1 h-4 w-4" />
                  {document.category}
                </span>
              )}
              <span className="inline-flex items-center">
                <Clock className="mr-1 h-4 w-4" />
                Updated {formatDate(document.updated_at)}
              </span>
            </div>

            {document.tags.length > 0 && (
              <div className="mt-4 flex items-center gap-2">
                <Tag className="h-4 w-4 text-slate-400 dark:text-slate-500" />
                {document.tags.map((tag) => (
                  <span
                    key={tag}
                    className="pill border-blue-200 bg-blue-100 text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          <PreviewToolbar
            previewableAttachments={[]}
            selectedAttachment={null}
            previewSource="inline"
            inlinePreviewAvailable
            onSelectAttachment={() => {}}
            onSelectInlinePreview={() => {}}
            readerError={null}
            onRetryReaderView={() => {}}
            fontSize={fontSize}
            onSetFontSize={handleSetFontSize}
            theme={theme}
            onSetTheme={handleSetTheme}
          />

          <div className="relative p-6">
            {tocSections.length > 1 ? (
              <div className="mb-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950 lg:hidden">
                <p className="helper-copy mb-3 uppercase tracking-[0.18em]">Contents</p>
                <div className="space-y-1">
                  {tocSections.map((section) => {
                    const anchorId = section.anchorId || `heading-${section.index}`;
                    const isActive = activeHeading === anchorId;
                    return (
                      <button
                        key={section.id}
                        type="button"
                        onClick={() => handleSectionClick(section)}
                        className={`block w-full rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                          isActive
                            ? 'bg-blue-100 font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-200'
                            : 'text-slate-600 hover:bg-blue-50 hover:text-blue-700 dark:text-slate-300 dark:hover:bg-slate-900'
                        }`}
                        style={{ paddingLeft: `${(section.level - 1) * 12 + 12}px` }}
                      >
                        {section.text}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}

            <div className="items-start gap-6 lg:flex">
              {tocSections.length > 1 ? (
                <div className="hidden h-[70vh] flex-shrink-0 self-start lg:block">
                  <TocPanel
                    sections={tocSections}
                    tocCollapsed={tocCollapsed}
                    onToggleCollapsed={() => setTocCollapsed((previous) => !previous)}
                    activeHeading={activeHeading}
                    readerCurrentPage={null}
                    isEditor={false}
                    showingReaderView={false}
                    sectionLinkBasePath={sectionLinkBasePath}
                    onSectionClick={handleSectionClick}
                    onEditSection={() => {}}
                  />
                </div>
              ) : null}

              <div className="min-w-0 flex-1 lg:flex lg:items-start lg:gap-6">
                <div className="min-w-0 flex-1">
                  <div
                    className={`${documentPaperClass} rounded-2xl`}
                    data-testid="customer-document-paper"
                  >
                    <div
                      ref={contentRef}
                      id="document-content-area"
                      onPointerUp={handleSelectionMouseUp}
                      className={`document-preview-content prose ${
                        contentWidth === 'reading' ? 'mx-auto max-w-3xl' : 'max-w-none'
                      }`}
                      style={contentStyle}
                    >
                      {renderedContent}
                    </div>
                  </div>
                </div>

                <div ref={commentsSidebarRef} className="mt-6 lg:mt-0 lg:w-[22rem] lg:flex-shrink-0">
                  <DocumentCommentsSidebar
                    threads={commentThreads}
                    isLoading={commentsQuery.isLoading}
                    isError={commentsQuery.isError}
                    showResolved={showResolvedComments}
                    activeThreadId={activeCommentThreadId}
                    canResolveThreads={false}
                    resolveMutationPending={toggleCommentResolutionMutation.isPending}
                    submittingReplyThreadId={submittingReplyThreadId}
                    onToggleShowResolved={setShowResolvedComments}
                    onThreadSelect={handleSelectCommentThread}
                    onToggleThreadResolved={handleToggleCommentThreadResolved}
                    onSubmitReply={handleSubmitCommentReply}
                  />
                </div>
              </div>
            </div>

            <InlineCommentPopups
              hasUser={Boolean(user)}
              selectionPopup={selectionPopup}
              commentPopup={commentPopup}
              commentText={commentText}
              isPrivateComment={false}
              showPrivateOption={false}
              isSubmittingComment={isSubmittingComment}
              topOffset={isFullscreen ? 76 : 0}
              onOpenCommentForm={handleOpenCommentForm}
              onCloseCommentPopup={closeCommentPopup}
              onCommentTextChange={setCommentText}
              onPrivateCommentChange={() => {}}
              onSubmitComment={handleSubmitComment}
            />
          </div>
        </div>

        {document.attachments.length > 0 && (
          <div className="surface-card rounded-2xl">
            <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <h2 className="section-title flex items-center dark:text-slate-100">
                <Paperclip className="mr-2 h-5 w-5" />
                Attachments ({document.attachments.length})
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {document.attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-950"
                  >
                    <div className="flex min-w-0 items-center">
                      <FileText className="h-8 w-8 flex-shrink-0 text-slate-400 dark:text-slate-500" />
                      <div className="ml-3 min-w-0">
                        <p className="card-title truncate dark:text-slate-100">
                          {attachment.filename}
                        </p>
                        <p className="helper-copy dark:text-slate-400">
                          {formatFileSize(attachment.file_size)}
                          {attachment.mime_type && ` - ${attachment.mime_type}`}
                        </p>
                      </div>
                    </div>
                    <a
                      href={
                        attachment.download_url ??
                        `/api/v1/documents/${document.id}/attachments/${attachment.id}/download`
                      }
                      className="btn-primary table-action-btn ml-4"
                    >
                      <Download className="mr-1 h-4 w-4" />
                      Download
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {relatedDocs && relatedDocs.length > 0 && (
          <div className="surface-card rounded-2xl">
            <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <h2 className="section-title flex items-center dark:text-slate-100">
                <BookOpen className="mr-2 h-5 w-5" />
                Related Documents
              </h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {relatedDocs.map((related) => (
                  <Link
                    key={related.id}
                    to={`/portal/documents/${related.id}`}
                    className="surface-card-hover block rounded-2xl p-4"
                  >
                    <h3 className="card-title line-clamp-2 dark:text-slate-100">{related.title}</h3>
                    {related.description && (
                      <p className="body-copy mt-1 line-clamp-2 dark:text-slate-400">
                        {related.description}
                      </p>
                    )}
                    <div className="helper-copy mt-2 flex items-center gap-2 dark:text-slate-500">
                      {related.category && (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800 dark:text-slate-200">
                          {related.category}
                        </span>
                      )}
                      {related.updated_at && <span>{formatDate(related.updated_at)}</span>}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="surface-card rounded-2xl">
          <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <h2 className="section-title dark:text-slate-100">Submit Feedback</h2>
            <p className="body-copy dark:text-slate-400">
              Have a question or suggestion about this document? Let us know. You can also
              highlight text above to add inline comments in the comments panel.
            </p>
          </div>
          <div className="p-6">
            {submittedFeedback ? (
              <div className="py-8 text-center">
                <CheckCircle className="mx-auto h-12 w-12 text-emerald-500" />
                <h3 className="section-title mt-4 text-base dark:text-slate-100">
                  Thank you for your feedback!
                </h3>
                <p className="body-copy mt-2 dark:text-slate-400">
                  Your feedback was sent to the team. We’ll respond in your feedback history when
                  needed.
                </p>
                <div className="mt-4 flex justify-center gap-4">
                  <button
                    onClick={() => setSubmittedFeedback(null)}
                    className="btn-secondary table-action-btn"
                    type="button"
                  >
                    Submit another
                  </button>
                  {submittedFeedback.ticket_id ? (
                    <Link
                      to={`/portal/support?ticket=${submittedFeedback.ticket_id}`}
                      className="btn-primary table-action-btn"
                    >
                      Open Support Conversation
                    </Link>
                  ) : null}
                  <Link to="/portal/feedback" className="btn-secondary table-action-btn">
                    View my feedback
                  </Link>
                </div>
              </div>
            ) : (
              <FeedbackForm
                onSubmit={(data) => feedbackMutation.mutate(data)}
                isLoading={feedbackMutation.isPending}
                error={feedbackMutation.error?.message}
              />
            )}
          </div>
        </div>

        <div className="surface-card flex items-center justify-between rounded-2xl px-6 py-5">
          <div>
            <h2 className="section-title dark:text-slate-100">Need more help?</h2>
            <p className="body-copy dark:text-slate-400">
              Open a support ticket with this document's context pre-filled.
            </p>
          </div>
          <Link
            to={`/portal/support?new=1&subject=${encodeURIComponent(`Help with: ${document?.title ?? 'Document #' + id}`)}&content=${encodeURIComponent(`Document: ${document?.title ?? ''} (ID: ${id})\nURL: ${window.location.href}\nBrowser: ${navigator.userAgent}\n\nDescribe your issue:\n`)}`}
            className="btn-primary table-action-btn inline-flex items-center gap-2 whitespace-nowrap"
          >
            <LifeBuoy className="h-4 w-4" />
            Contact Support
          </Link>
        </div>
      </div>
    </div>
  );
}
