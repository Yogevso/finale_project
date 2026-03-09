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
  return (
    <div className="document-detail-header-card rounded-3xl bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg overflow-hidden">
      <div className="px-6 py-5 md:px-8 md:py-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <button
            onClick={onBackToDocuments}
            className="inline-flex items-center gap-2 text-sm text-sky-100/80 hover:text-white mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Documents
          </button>
          <h1 className="text-2xl md:text-3xl font-display font-bold">{documentTitle}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-sky-100/80">
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
            onClick={onPrint}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
            title="Print document"
          >
            <Printer className="w-4 h-4" />
            Print
          </button>

          {dueDate && onExportCalendar ? (
            <button
              onClick={onExportCalendar}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
              title="Export due date as iCal"
            >
              <CalendarDays className="w-4 h-4" />
              Export iCal
            </button>
          ) : null}

          {!isFullscreen ? (
            <button
              onClick={onEnterFullscreen}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
              title="Toggle fullscreen (F)"
            >
              <Maximize2 className="w-4 h-4" />
              Fullscreen
            </button>
          ) : (
            <button
              onClick={onExitFullscreen}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
              title="Toggle fullscreen (F)"
            >
              <Minimize2 className="w-4 h-4" />
              Exit Fullscreen
            </button>
          )}

          {isEditor && (
            <>
              {documentStatus === 'draft' && (
                <button
                  onClick={onOpenSubmitReview}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white text-sky-900 hover:bg-slate-100 transition-colors"
                >
                  <Send className="w-4 h-4" />
                  Submit for Review
                </button>
              )}
              {documentStatus === 'pending_review' && (
                <span className="flex items-center gap-2 px-4 py-2 bg-amber-200/30 text-amber-100 rounded-lg">
                  <Clock className="w-4 h-4" />
                  Pending Review
                </span>
              )}
              {documentStatus === 'approved' && (
                <span className="flex items-center gap-2 px-4 py-2 bg-sky-200/30 text-sky-100 rounded-lg">
                  <CheckCircle className="w-4 h-4" />
                  Approved (Ready to Publish)
                </span>
              )}
              <button
                onClick={onEditAction}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
              >
                {activeTab === 'details'
                  ? isEditing
                    ? 'Cancel Details'
                    : 'Edit Details'
                  : 'Edit Content'}
              </button>
              <button
                onClick={documentStatus === 'archived' ? onRestore : onArchive}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
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
          )}
        </div>
      </div>
    </div>
  )
}
