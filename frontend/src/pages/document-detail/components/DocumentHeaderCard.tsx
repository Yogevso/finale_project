import type { DocumentStatus } from '@/types'
import { formatDueDate } from '@/lib/documentDueDates'
import { getDocumentDisplayTitle } from '@/lib/documentDisplay'
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle,
  Clock,
  Download,
  FileText,
  HelpCircle,
  Maximize2,
  RotateCcw,
  Send,
  Trash2,
  XCircle,
} from 'lucide-react'
import { useState } from 'react'
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
  sourceFileType = 'other',
  onBackToDocuments,
  onEnterFullscreen,
  onExitFullscreen: _onExitFullscreen,
  onGenerateTranscript,
  onExportCalendar,
  onOpenSubmitReview,
  onCancelReview,
  isCancellingReview,
  onEditAction,
  onArchive,
  onRestore,
  onDownloadAs,
  onHelp,
  removedSectionsCount = 0,
  onShowRemovedSections,
}: DocumentHeaderCardProps) {
  const [showDownloadMenu, setShowDownloadMenu] = useState(false)

  const resolvedDocumentTitle = getDocumentDisplayTitle(documentTitle)
  const headerActionClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 text-white transition-colors hover:bg-white/20'
  const headerStatusClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 text-white/90'

  const showWordDownload = sourceFileType === 'word' || sourceFileType === 'pdf'
  const showPptDownload = sourceFileType === 'ppt'

  return (
    <div className="document-detail-header-card sticky top-0 z-30 overflow-hidden rounded-3xl bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg">
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
          <h1 className="page-title max-w-4xl leading-tight md:text-3xl !text-white [overflow-wrap:anywhere]">
            {resolvedDocumentTitle}
          </h1>
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
          {onGenerateTranscript && (
            <button
              type="button"
              onClick={onGenerateTranscript}
              className={headerActionClassName}
              title="Generate transcript"
            >
              <FileText className="w-4 h-4" />
              Generate Transcript
            </button>
          )}

          {onDownloadAs && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowDownloadMenu((p) => !p)}
                className={headerActionClassName}
                title="Download options"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
              {showDownloadMenu && (
                <>
                  <button
                    type="button"
                    className="fixed inset-0 z-40 bg-transparent"
                    onClick={() => setShowDownloadMenu(false)}
                    aria-label="Close download menu"
                  />
                  <div className="absolute right-0 top-full z-50 mt-1 w-44 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                    <button
                      type="button"
                      onClick={() => { setShowDownloadMenu(false); onDownloadAs('pdf') }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-700"
                    >
                      PDF
                    </button>
                    {showWordDownload && (
                      <button
                        type="button"
                        onClick={() => { setShowDownloadMenu(false); onDownloadAs('word') }}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-700"
                      >
                        Word (.docx)
                      </button>
                    )}
                    {showPptDownload && (
                      <button
                        type="button"
                        onClick={() => { setShowDownloadMenu(false); onDownloadAs('ppt') }}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-700"
                      >
                        PowerPoint (.pptx)
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

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

          {!isFullscreen && (
            <button
              type="button"
              onClick={onEnterFullscreen}
              className={headerActionClassName}
              title="Toggle fullscreen (F)"
            >
              <Maximize2 className="w-4 h-4" />
              Fullscreen
            </button>
          )}

          {isEditor ? (
            <>
              {documentStatus !== 'archived' ? (
                <button
                  type="button"
                  onClick={onOpenSubmitReview}
                  className="btn-secondary table-action-btn border-white/60 bg-white text-sky-900 hover:border-white hover:bg-slate-100"
                >
                  <Send className="w-4 h-4" />
                  {documentStatus === 'pending_review'
                    ? 'Resubmit for Review'
                    : documentStatus === 'active'
                      ? 'Submit Draft for Review'
                      : documentStatus === 'approved'
                        ? 'Submit New Review'
                        : 'Submit for Review'}
                </button>
              ) : null}
              {documentStatus === 'pending_review' ? (
                <span className={headerStatusClassName}>
                  <Clock className="w-4 h-4" />
                  Pending Review
                </span>
              ) : null}
              {documentStatus === 'pending_review' && onCancelReview ? (
                <button
                  type="button"
                  onClick={onCancelReview}
                  disabled={isCancellingReview}
                  className="table-action-btn inline-flex items-center gap-2 rounded-full border border-rose-300/40 bg-rose-500/20 text-white transition-colors hover:bg-rose-500/40 disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  {isCancellingReview ? 'Cancelling...' : 'Cancel Review'}
                </button>
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
                  : 'Edit Document'}
              </button>
              <button
                type="button"
                onClick={documentStatus === 'archived' ? onRestore : (onShowRemovedSections ?? onArchive)}
                className={headerActionClassName}
              >
                {documentStatus === 'archived' ? (
                  <>
                    <RotateCcw className="w-4 h-4" />
                    Restore
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Removed Sections
                    {removedSectionsCount > 0 && (
                      <span className="ml-0.5 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-white/25 px-1 text-xs font-bold">
                        {removedSectionsCount}
                      </span>
                    )}
                  </>
                )}
              </button>
            </>
          ) : null}

          {onHelp && (
            <button
              type="button"
              onClick={onHelp}
              className={headerActionClassName}
              title="Help"
            >
              <HelpCircle className="w-4 h-4" />
              Help
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
