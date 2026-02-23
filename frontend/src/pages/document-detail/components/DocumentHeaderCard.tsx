import type { DocumentStatus } from '@/types'
import { CheckCircle, Clock, Maximize2, Minimize2, Send } from 'lucide-react'

type HeaderTab = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

interface DocumentHeaderCardProps {
  documentTitle: string
  documentNumber: string
  isFullscreen: boolean
  isEditor: boolean
  documentStatus: DocumentStatus
  activeTab: HeaderTab
  isEditing: boolean
  onBackToDocuments: () => void
  onEnterFullscreen: () => void
  onExitFullscreen: () => void
  onOpenSubmitReview: () => void
  onEditAction: () => void
  onDelete: () => void
}

export function DocumentHeaderCard({
  documentTitle,
  documentNumber,
  isFullscreen,
  isEditor,
  documentStatus,
  activeTab,
  isEditing,
  onBackToDocuments,
  onEnterFullscreen,
  onExitFullscreen,
  onOpenSubmitReview,
  onEditAction,
  onDelete,
}: DocumentHeaderCardProps) {
  return (
    <div className="rounded-3xl bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg overflow-hidden">
      <div className="px-6 py-5 md:px-8 md:py-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <button
            onClick={onBackToDocuments}
            className="text-sm text-sky-100/80 hover:text-white mb-2"
          >
            {'<-'} Back to Documents
          </button>
          <h1 className="text-2xl md:text-3xl font-display font-bold">{documentTitle}</h1>
          <p className="text-sky-100/80 mt-1">{documentNumber}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {!isFullscreen ? (
            <button
              onClick={onEnterFullscreen}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
              title="Open Fullscreen View"
            >
              <Maximize2 className="w-4 h-4" />
              Fullscreen
            </button>
          ) : (
            <button
              onClick={onExitFullscreen}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition-colors text-white"
              title="Exit Fullscreen View"
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
                onClick={onDelete}
                className="px-4 py-2 bg-rose-500 text-white rounded-lg hover:bg-rose-600"
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
