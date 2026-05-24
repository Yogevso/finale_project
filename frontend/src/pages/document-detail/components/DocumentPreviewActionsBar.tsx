import { useState } from 'react'
import type { DocumentStatus } from '@/types'
import {
  CalendarDays,
  Download,
  FileText,
  HelpCircle,
  MoreHorizontal,
  RotateCcw,
  Send,
  Trash2,
  XCircle,
} from 'lucide-react'

type SourceFileType = 'word' | 'pdf' | 'ppt' | 'other'

interface DocumentPreviewActionsBarProps {
  isEditor: boolean
  documentStatus: DocumentStatus
  sourceFileType?: SourceFileType
  dueDate?: string | null
  onGenerateTranscript?: () => void
  onDownloadAs?: (format: 'word' | 'pdf' | 'ppt') => void
  onExportCalendar?: () => void
  onOpenSubmitReview: () => void
  onCancelReview?: () => void
  isCancellingReview?: boolean
  onEditAction: () => void
  onArchive: () => void
  onRestore: () => void
  onHelp?: () => void
  removedSectionsCount?: number
  onShowRemovedSections?: () => void
  isRevamp?: boolean
}

export function DocumentPreviewActionsBar({
  isEditor,
  documentStatus,
  sourceFileType = 'other',
  dueDate,
  onGenerateTranscript,
  onDownloadAs,
  onExportCalendar,
  onOpenSubmitReview,
  onCancelReview,
  isCancellingReview,
  onEditAction,
  onArchive,
  onRestore,
  onHelp,
  removedSectionsCount = 0,
  onShowRemovedSections,
  isRevamp = false,
}: DocumentPreviewActionsBarProps) {
  const [showDownloadMenu, setShowDownloadMenu] = useState(false)
  const [showOverflowMenu, setShowOverflowMenu] = useState(false)

  const actionClassName =
    'table-action-btn inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700'
  const primaryClassName =
    'table-action-btn inline-flex h-8 items-center gap-1.5 rounded-lg border border-blue-600 bg-blue-600 px-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700'
  const dangerClassName =
    'table-action-btn inline-flex h-8 items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 text-sm font-medium text-rose-700 transition-colors hover:border-rose-300 hover:bg-rose-100 disabled:opacity-50'
  const overflowTriggerClassName =
    'table-action-btn inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700'

  const showWordDownload = sourceFileType === 'word' || sourceFileType === 'pdf'
  const showPptDownload = sourceFileType === 'ppt'
  const showRemovedSectionsAction = isEditor
  const showExportCalendarAction = Boolean(dueDate && onExportCalendar)
  const showHelpAction = Boolean(onHelp)
  const shouldShowOverflowMenu =
    isRevamp && (showRemovedSectionsAction || showExportCalendarAction || showHelpAction)

  return (
    <div className={`flex flex-wrap items-center gap-2 ${isRevamp ? 'justify-between' : ''}`}>
      <div className="flex flex-wrap items-center gap-2">
      {onGenerateTranscript && (
        <button
          type="button"
          onClick={onGenerateTranscript}
          className={actionClassName}
          title="Generate transcript"
        >
          <FileText className="h-4 w-4" />
          Generate Transcript
        </button>
      )}

      {onDownloadAs && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowDownloadMenu((previous) => !previous)}
            className={actionClassName}
            title="Download options"
          >
            <Download className="h-4 w-4" />
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
              <div className="absolute left-0 top-full z-50 mt-1 w-44 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                <button
                  type="button"
                  onClick={() => {
                    setShowDownloadMenu(false)
                    onDownloadAs('pdf')
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                >
                  PDF
                </button>
                {showWordDownload && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowDownloadMenu(false)
                      onDownloadAs('word')
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                  >
                    Word (.docx)
                  </button>
                )}
                {showPptDownload && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowDownloadMenu(false)
                      onDownloadAs('ppt')
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                  >
                    PowerPoint (.pptx)
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {isEditor ? (
        <>
          {documentStatus !== 'archived' ? (
            <button type="button" onClick={onOpenSubmitReview} className={primaryClassName}>
              <Send className="h-4 w-4" />
              {documentStatus === 'pending_review'
                ? 'Resubmit for Review'
                : documentStatus === 'active'
                  ? 'Submit Draft for Review'
                  : documentStatus === 'approved'
                    ? 'Submit New Review'
                    : 'Submit for Review'}
            </button>
          ) : null}
          {documentStatus === 'pending_review' && onCancelReview ? (
            <button
              type="button"
              onClick={onCancelReview}
              disabled={isCancellingReview}
              className={dangerClassName}
            >
              <XCircle className="h-4 w-4" />
              {isCancellingReview ? 'Cancelling...' : 'Cancel Review'}
            </button>
          ) : null}
          <button type="button" onClick={onEditAction} className={actionClassName}>
            Edit Document
          </button>
          {!isRevamp && (
            <button
              type="button"
              onClick={documentStatus === 'archived' ? onRestore : (onShowRemovedSections ?? onArchive)}
              className={actionClassName}
            >
              {documentStatus === 'archived' ? (
                <>
                  <RotateCcw className="h-4 w-4" />
                  Restore
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4" />
                  Removed Sections
                  {removedSectionsCount > 0 && (
                    <span className="ml-0.5 inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-slate-100 px-1 text-[10px] font-bold text-slate-700">
                      {removedSectionsCount}
                    </span>
                  )}
                </>
              )}
            </button>
          )}
        </>
      ) : null}

      {!isRevamp && dueDate && onExportCalendar ? (
        <button
          type="button"
          onClick={onExportCalendar}
          className={actionClassName}
          title="Export due date as iCal"
        >
          <CalendarDays className="h-4 w-4" />
          Export iCal
        </button>
      ) : null}

      {!isRevamp && onHelp && (
        <button type="button" onClick={onHelp} className={actionClassName} title="Help">
          <HelpCircle className="h-4 w-4" />
          Help
        </button>
      )}
      </div>

      {shouldShowOverflowMenu && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowOverflowMenu((previous) => !previous)}
            className={overflowTriggerClassName}
            aria-haspopup="menu"
            aria-expanded={showOverflowMenu}
            title="More actions"
          >
            <MoreHorizontal className="h-4 w-4" />
            More
          </button>
          {showOverflowMenu && (
            <>
              <button
                type="button"
                className="fixed inset-0 z-40 bg-transparent"
                onClick={() => setShowOverflowMenu(false)}
                aria-label="Close actions menu"
              />
              <div className="absolute right-0 top-full z-50 mt-1 min-w-[15rem] rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                {showRemovedSectionsAction ? (
                  <button
                    type="button"
                    onClick={() => {
                      setShowOverflowMenu(false)
                      if (documentStatus === 'archived') {
                        onRestore()
                        return
                      }
                      const openRemovedSections = onShowRemovedSections ?? onArchive
                      openRemovedSections()
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                  >
                    {documentStatus === 'archived' ? (
                      <>
                        <RotateCcw className="h-4 w-4" />
                        Restore
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4" />
                        Removed Sections
                        {removedSectionsCount > 0 && (
                          <span className="ml-0.5 inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-slate-100 px-1 text-[10px] font-bold text-slate-700">
                            {removedSectionsCount}
                          </span>
                        )}
                      </>
                    )}
                  </button>
                ) : null}
                {showExportCalendarAction ? (
                  <button
                    type="button"
                    onClick={() => {
                      setShowOverflowMenu(false)
                      onExportCalendar?.()
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                  >
                    <CalendarDays className="h-4 w-4" />
                    Export iCal
                  </button>
                ) : null}
                {showHelpAction ? (
                  <button
                    type="button"
                    onClick={() => {
                      setShowOverflowMenu(false)
                      onHelp?.()
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                  >
                    <HelpCircle className="h-4 w-4" />
                    Help
                  </button>
                ) : null}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
