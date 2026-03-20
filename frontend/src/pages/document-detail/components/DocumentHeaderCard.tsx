import type { DocumentStatus } from '@/types'
import { formatDueDate } from '@/lib/documentDueDates'
import {
  AlertTriangle,
  Archive,
  ArrowLeft,
  CalendarDays,
  CheckCircle,
  Clock,
  Maximize2,
  Minimize2,
  Printer,
  RotateCcw,
  Send,
} from 'lucide-react'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'

type HeaderTab = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

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
  onBackToDocuments: () => void
  onEnterFullscreen: () => void
  onExitFullscreen: () => void
  onPrint: () => void
  onExportCalendar?: () => void
  onOpenSubmitReview: () => void
  onEditAction: () => void
  onArchive: () => void
  onRestore: () => void
}

export function DocumentHeaderCard({
  documentId,
  documentTitle,
  documentNumber,
  readingTimeMinutes,
  dueDate,
  isOverdue,
  isFullscreen,
  isEditor,
  documentStatus,
  activeTab,
  isEditing,
  onBackToDocuments,
  onEnterFullscreen,
  onExitFullscreen,
  onPrint,
  onExportCalendar,
  onOpenSubmitReview,
  onEditAction,
  onArchive,
  onRestore,
}: DocumentHeaderCardProps) {
  const headerActionClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 text-white transition-colors hover:bg-white/20'
  const headerStatusClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 text-white/90'

  return (
    <div className="document-detail-header-card overflow-hidden rounded-3xl bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg">
      <div className="flex flex-col gap-4 px-6 py-5 md:flex-row md:items-start md:justify-between md:px-8 md:py-6">
        <div>
          <button
            type="button"
            onClick={onBackToDocuments}
            className="helper-copy mb-2 inline-flex items-center gap-2 text-sky-100/80 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Documents
          </button>
          <h1 className="page-title md:text-3xl !text-white">{documentTitle}</h1>
          <p className="helper-copy mt-1 flex flex-wrap items-center gap-2 text-sky-100/80">
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
            <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-amber-200/50 bg-amber-300/15 px-3 py-1 text-xs font-semibold text-amber-50">
              <AlertTriangle className="h-3.5 w-3.5" />
              Overdue
            </div>
          ) : null}
          <div className="mt-3">
            <BookmarkToggleButton
              documentId={documentId}
              className="border-white/20 bg-white/10 text-white hover:bg-white/20"
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onPrint}
            className={headerActionClassName}
            title="Print document"
          >
            <Printer className="w-4 h-4" />
            Print
          </button>

          {dueDate && onExportCalendar ? (
            <button
              type="button"
              onClick={onExportCalendar}
              className={headerActionClassName}
              title="Export due date as iCal"
            >
              <CalendarDays className="w-4 h-4" />
              Export iCal
            </button>
          ) : null}

          {!isFullscreen ? (
            <button
              type="button"
              onClick={onEnterFullscreen}
              className={headerActionClassName}
              title="Toggle fullscreen (F)"
            >
              <Maximize2 className="w-4 h-4" />
              Fullscreen
            </button>
          ) : (
            <button
              type="button"
              onClick={onExitFullscreen}
              className={headerActionClassName}
              title="Toggle fullscreen (F)"
            >
              <Minimize2 className="w-4 h-4" />
              Exit Fullscreen
            </button>
          )}

          {isEditor ? (
            <>
              {documentStatus === 'draft' ? (
                <button
                  type="button"
                  onClick={onOpenSubmitReview}
                  className="btn-secondary table-action-btn border-white/60 bg-white text-sky-900 hover:border-white hover:bg-slate-100"
                >
                  <Send className="w-4 h-4" />
                  Submit for Review
                </button>
              ) : null}
              {documentStatus === 'pending_review' ? (
                <span className={headerStatusClassName}>
                  <Clock className="w-4 h-4" />
                  Pending Review
                </span>
              ) : null}
              {documentStatus === 'approved' ? (
                <span className={headerStatusClassName}>
                  <CheckCircle className="w-4 h-4" />
                  Approved (Ready to Publish)
                </span>
              ) : null}
              <button type="button" onClick={onEditAction} className={headerActionClassName}>
                {activeTab === 'details'
                  ? isEditing
                    ? 'Cancel Details'
                    : 'Edit Details'
                  : 'Edit Content'}
              </button>
              <button
                type="button"
                onClick={documentStatus === 'archived' ? onRestore : onArchive}
                className={headerActionClassName}
              >
                {documentStatus === 'archived' ? (
                  <>
                    <RotateCcw className="w-4 h-4" />
                    Restore
                  </>
                ) : (
                  <>
                    <Archive className="w-4 h-4" />
                    Archive
                  </>
                )}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
