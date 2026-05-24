import { useEffect, useState } from 'react'
import type { DocumentStatus } from '@/types'
import { formatDueDate } from '@/lib/documentDueDates'
import { getDocumentDisplayTitle } from '@/lib/documentDisplay'
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle,
  Clock,
  Maximize2,
} from 'lucide-react'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'

type HeaderTab = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

type SourceFileType = 'word' | 'pdf' | 'ppt' | 'other'

interface DocumentHeaderCardProps {
  documentId: number
  documentTitle: string
  documentNumber: string
  readingTimeMinutes?: number | null
  dueDate?: string | null
  isOverdue?: boolean
  isFullscreen: boolean
  isEditor: boolean
  documentStatus: DocumentStatus
  activeTab: HeaderTab
  isEditing: boolean
  sourceFileType?: SourceFileType
  onBackToDocuments: () => void
  onEnterFullscreen: () => void
  onExitFullscreen: () => void
  onGenerateTranscript?: () => void
  onExportCalendar?: () => void
  onOpenSubmitReview: () => void
  onCancelReview?: () => void
  isCancellingReview?: boolean
  onEditAction: () => void
  onArchive: () => void
  onRestore: () => void
  onDownloadAs?: (format: 'word' | 'pdf' | 'ppt') => void
  onHelp?: () => void
  removedSectionsCount?: number
  onShowRemovedSections?: () => void
  isRevamp?: boolean
}

export function DocumentHeaderCard({
  documentId,
  documentTitle,
  documentNumber,
  readingTimeMinutes,
  dueDate,
  isOverdue,
  isFullscreen,
  isEditor: _isEditor,
  documentStatus,
  activeTab: _activeTab,
  isEditing: _isEditing,
  sourceFileType: _sourceFileType = 'other',
  onBackToDocuments,
  onEnterFullscreen,
  onExitFullscreen: _onExitFullscreen,
  onGenerateTranscript: _onGenerateTranscript,
  onExportCalendar: _onExportCalendar,
  onOpenSubmitReview: _onOpenSubmitReview,
  onCancelReview: _onCancelReview,
  isCancellingReview: _isCancellingReview,
  onEditAction: _onEditAction,
  onArchive: _onArchive,
  onRestore: _onRestore,
  onDownloadAs: _onDownloadAs,
  onHelp: _onHelp,
  removedSectionsCount: _removedSectionsCount = 0,
  onShowRemovedSections: _onShowRemovedSections,
  isRevamp = false,
}: DocumentHeaderCardProps) {
  const [isCondensed, setIsCondensed] = useState(false)
  const resolvedDocumentTitle = getDocumentDisplayTitle(documentTitle)
  const headerHeroActionClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 text-white transition-colors hover:bg-white/20'
  const headerStatusClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 text-white/90'
  const showPendingBadge = documentStatus === 'pending_review'
  const showApprovedBadge = documentStatus === 'approved'

  useEffect(() => {
    if (!isRevamp) {
      setIsCondensed(false)
      return
    }

    const onScroll = () => {
      setIsCondensed(window.scrollY > 22)
    }

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [isRevamp])

  return (
    <div
      className={`document-detail-header-card overflow-hidden text-white transition-all duration-200 ${
        isRevamp
          ? `z-30 rounded-2xl border border-blue-200/55 bg-gradient-to-r from-blue-800 via-blue-700 to-blue-600 ${
              isCondensed ? 'shadow-[0_10px_22px_-14px_rgba(0,59,106,0.65)]' : 'shadow-lg'
            }`
          : isFullscreen
            ? 'relative rounded-3xl bg-gradient-to-br from-blue-800 via-blue-700 to-blue-600 shadow-lg'
            : 'z-30 rounded-3xl bg-gradient-to-l from-blue-800 via-blue-700 to-blue-600 shadow-lg'
      }`}
    >
      <div
        className={`${
          isRevamp
            ? isCondensed
              ? 'px-4 py-3 md:px-6 md:py-3'
              : 'px-5 py-4 md:px-7 md:py-4'
            : 'px-6 py-5 md:px-8 md:py-6'
        }`}
      >
        <div
          className={`flex flex-col gap-5 ${
            isFullscreen ? 'items-center text-center' : 'md:flex-row md:items-start md:justify-between'
          }`}
        >
          <div className={isFullscreen ? 'w-full max-w-4xl' : ''}>
            <button
              type="button"
              onClick={onBackToDocuments}
              className={`helper-copy mb-2 inline-flex items-center gap-2 text-blue-100/80 hover:text-white ${
                isFullscreen ? 'self-start' : ''
              }`}
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Documents
            </button>
            <h1
              className={`page-title leading-tight !text-white [overflow-wrap:anywhere] ${
                isRevamp
                  ? isCondensed
                    ? 'max-w-3xl text-2xl md:text-[1.8rem]'
                    : 'max-w-4xl text-[2rem] md:text-[2.35rem]'
                  : isFullscreen
                    ? 'max-w-5xl text-3xl md:text-4xl'
                    : 'max-w-4xl md:text-3xl'
              }`}
            >
              {resolvedDocumentTitle}
            </h1>
            <p
              className={`helper-copy mt-2 flex flex-wrap items-center gap-2 text-blue-100/80 ${
                isFullscreen ? 'justify-center text-sm md:text-base' : ''
              }`}
            >
              <span>{documentNumber}</span>
              {readingTimeMinutes ? (
                <>
                  <span className="h-1 w-1 rounded-full bg-white/60" aria-hidden="true" />
                  <span>~{readingTimeMinutes} min read</span>
                </>
              ) : null}
              {dueDate ? (
                <>
                  <span className="h-1 w-1 rounded-full bg-white/60" aria-hidden="true" />
                  <span className="inline-flex items-center gap-1">
                    <CalendarDays className="h-3.5 w-3.5" />
                    Due {formatDueDate(dueDate)}
                  </span>
                </>
              ) : null}
            </p>
            {isOverdue ? (
              <div
                className={`mt-3 inline-flex items-center gap-2 rounded-full border border-amber-200/50 bg-amber-300/15 px-3 py-1 text-xs font-semibold text-amber-50 ${
                  isFullscreen ? 'mx-auto' : ''
                }`}
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                Overdue
              </div>
            ) : null}
            <div className={`mt-3 ${isFullscreen ? 'flex justify-center' : ''}`}>
              <BookmarkToggleButton
                documentId={documentId}
                className="border-white/20 bg-white/10 text-white hover:bg-white/20"
              />
            </div>
            {isFullscreen && (showPendingBadge || showApprovedBadge) ? (
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                {showPendingBadge ? (
                  <span className={headerStatusClassName}>
                    <Clock className="w-4 h-4" />
                    Pending Review
                  </span>
                ) : null}
                {showApprovedBadge ? (
                  <span className={headerStatusClassName}>
                    <CheckCircle className="w-4 h-4" />
                    Approved (Ready to Publish)
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>

          {!isFullscreen ? (
            <div className="flex flex-wrap items-center gap-2 md:justify-end">
              {showPendingBadge ? (
                <span className={headerStatusClassName}>
                  <Clock className="w-4 h-4" />
                  Pending Review
                </span>
              ) : null}
              {showApprovedBadge ? (
                <span className={headerStatusClassName}>
                  <CheckCircle className="w-4 h-4" />
                  Approved (Ready to Publish)
                </span>
              ) : null}
              <button
                type="button"
                onClick={onEnterFullscreen}
                className={headerHeroActionClassName}
                title="Toggle fullscreen (F)"
              >
                <Maximize2 className="w-4 h-4" />
                Fullscreen
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
