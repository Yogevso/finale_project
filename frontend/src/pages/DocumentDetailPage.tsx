import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Joyride from 'react-joyride'
import { DocumentPreview } from '@/pages/document-detail/DocumentPreview'
import { EditForm } from '@/pages/document-detail/EditForm'
import { DocumentDetailsView } from '@/pages/document-detail/components/DocumentDetailsView'
import { DocumentHeaderCard } from '@/pages/document-detail/components/DocumentHeaderCard'
import { DocumentTabs } from '@/pages/document-detail/components/DocumentTabs'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'
import { ReviewSubmitModal } from '@/pages/document-detail/components/ReviewSubmitModal'
import { HelpPanel } from '@/pages/document-detail/components/HelpPanel'
import { RemovedSectionsPanel } from '@/pages/document-detail/components/RemovedSectionsPanel'
import { useDocumentDetailPageState } from '@/pages/document-detail/hooks/useDocumentDetailPageState'
import type { RemovedSection } from '@/pages/document-detail/hooks/useContentEditingFlow'
import { api } from '@/lib/api'
import EngagementBar from '@/components/EngagementBar'
import { useTour } from '@/hooks/useTour'
import { documentDetailTour } from '@/lib/tour'
import NotFoundState from '@/components/NotFoundState'

const VersionsSection = lazy(() => import('@/components/VersionsSection'))
const AttachmentsSection = lazy(() => import('@/components/AttachmentsSection'))
// Comments tab removed — comments are accessible via inline popups

export default function DocumentDetailPage() {
  const tour = useTour('document-detail', documentDetailTour)
  const [readingTimeMinutes, setReadingTimeMinutes] = useState<number | null>(null)
  const [showHelp, setShowHelp] = useState(false)
  const [showRemovedSections, setShowRemovedSections] = useState(false)
  const [removedSections, setRemovedSections] = useState<RemovedSection[]>([])
  const restoreSectionRef = useRef<(s: RemovedSection) => void>(() => {})
  const clearRemovedSectionsRef = useRef<() => void>(() => {})
  const [searchParams] = useSearchParams()
  const highlightText = searchParams.get('highlight') || undefined
  const {
    documentId,
    document,
    isLoading,
    error,
    isEditor,
    isManager,
    isFullscreen,
    isEditing,
    setIsEditing,
    activeTab,
    setActiveTab,
    scrollProgress,
    handleScrollProgress,
    contentEditRequestToken,
    showCompanySelector,
    toggleCompanySelector,
    assignmentDraftCompanyIds,
    hasUnsavedAssignmentChanges,
    updateAssignmentDraft,
    saveAssignmentDraft,
    discardAssignmentDraft,
    showSubmitReview,
    submitMessage,
    setSubmitMessage,
    openSubmitReview,
    closeSubmitReview,
    submitReview,
    submitReviewErrorMessage,
    contentWidth,
    contentWidthClass,
    readingModeClass,
    applyWidth,
    attachments,
    assignedCompanies,
    audienceAccessPreview,
    reviewHistoryItems,
    navigateToDocuments,
    navigateToFullscreen,
    navigateToDetail,
    exportCalendar,
    handleArchive,
    handleEditAction,
    handleRestore,
    isArchivingDocument,
    isOverdue,
    updateDocument,
    isUpdatingDocument,
    isAssigningCompanies,
    removeCompany,
    isRemovingCompany,
    isSubmittingReview,
    pendingReviewId,
    cancelReview,
    isCancellingReview,
  } = useDocumentDetailPageState()

  useEffect(() => {
    setReadingTimeMinutes(null)
  }, [documentId])

  const handleRemovedSectionsChange = useCallback(
    (sections: RemovedSection[], restore: (s: RemovedSection) => void, clear: () => void) => {
      setRemovedSections(sections)
      restoreSectionRef.current = restore
      clearRemovedSectionsRef.current = clear
    },
    [],
  )

  // Clear removed sections storage when status becomes approved
  const prevStatusRef = useRef(document?.status)
  useEffect(() => {
    if (document?.status === 'approved' && prevStatusRef.current !== 'approved') {
      clearRemovedSectionsRef.current()
    }
    prevStatusRef.current = document?.status
  }, [document?.status])

  const tabCounts = {
    versions: document?.versions_count ?? 0,
    attachments: document?.attachments_count ?? attachments.length,
  }

  if (isLoading) {
    return (
      <div className="content-shell flex h-64 animate-fade-in flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-sky-600" />
        <p className="body-copy">Loading document...</p>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="animate-fade-in">
        <NotFoundState
          title="Document Not Found"
          description="This document may not exist or you may not have access."
        />
      </div>
    )
  }

  const sourceFileType = (() => {
    const first = attachments[0]
    if (!first) return 'other' as const
    const mime = first.mime_type?.toLowerCase() ?? ''
    const name = first.original_filename?.toLowerCase() ?? ''
    if (mime.includes('presentation') || mime.includes('powerpoint') || name.endsWith('.pptx') || name.endsWith('.ppt'))
      return 'ppt' as const
    if (mime.includes('word') || mime.includes('msword') || name.endsWith('.docx') || name.endsWith('.doc'))
      return 'word' as const
    if (mime === 'application/pdf' || name.endsWith('.pdf'))
      return 'pdf' as const
    return 'other' as const
  })()

  return (
    <div
      className={`document-detail-page animate-fade-in ${isFullscreen ? 'min-h-screen bg-slate-50 px-6 py-6 md:px-10 lg:px-14' : 'page-stack'}`}
    >
      <Joyride
        steps={documentDetailTour}
        run={tour.run}
        callback={tour.onJoyrideCallback}
        continuous
        showProgress
        showSkipButton
        disableScrolling
        disableOverlay
      />

      <FullscreenTopBar
        isFullscreen={isFullscreen}
        documentTitle={document.title}
        contentWidth={contentWidth}
        onExitFullscreen={navigateToDetail}
        onSetReadingWidth={() => applyWidth('reading')}
        onSetFluidWidth={() => applyWidth('fluid')}
      />

      <div
        className={`space-y-6 ${readingModeClass} ${
          isFullscreen ? `w-full ${contentWidthClass} mx-auto` : ''
        }`}
      >
        <DocumentHeaderCard
          documentId={document.id}
          documentTitle={document.title}
          documentNumber={document.document_number}
          readingTimeMinutes={readingTimeMinutes}
          dueDate={document.due_date}
          isOverdue={isOverdue}
          isFullscreen={isFullscreen}
          isEditor={isEditor}
          documentStatus={document.status}
          activeTab={activeTab}
          isEditing={isEditing}
          sourceFileType={sourceFileType}
          onBackToDocuments={navigateToDocuments}
          onEnterFullscreen={navigateToFullscreen}
          onExitFullscreen={navigateToDetail}
          onGenerateTranscript={() => window.print()}
          onExportCalendar={document.due_date ? exportCalendar : undefined}
          onOpenSubmitReview={openSubmitReview}
          onCancelReview={pendingReviewId ? () => cancelReview() : undefined}
          isCancellingReview={isCancellingReview}
          onEditAction={handleEditAction}
          onArchive={handleArchive}
          onRestore={handleRestore}
          onDownloadAs={(format) => {
            const formatMap: Record<string, 'pdf' | 'docx' | 'pptx'> = {
              pdf: 'pdf',
              word: 'docx',
              ppt: 'pptx',
            }
            const apiFormat = formatMap[format]
            if (!apiFormat) return
            void (async () => {
              try {
                const blob = await api.exportDocument(documentId, apiFormat)
                const url = URL.createObjectURL(blob)
                const link = Object.assign(window.document.createElement('a'), {
                  href: url,
                  download: `${document.title || 'document'}.${apiFormat}`,
                })
                link.click()
                URL.revokeObjectURL(url)
              } catch {
                console.error('Export failed')
              }
            })()
          }}
          onHelp={() => setShowHelp(true)}
          removedSectionsCount={removedSections.length}
          onShowRemovedSections={() => setShowRemovedSections(true)}
        />

        <EngagementBar
          documentId={documentId}
          scrollProgress={activeTab === 'preview' ? scrollProgress : undefined}
        />

        <DocumentTabs activeTab={activeTab} onTabChange={setActiveTab} counts={tabCounts} />

        {activeTab === 'preview' && (
          <DocumentPreview
            documentId={documentId}
            attachments={attachments}
            documentTitle={document.title}
            onScrollProgress={handleScrollProgress}
            onReadingTimeChange={setReadingTimeMinutes}
            isEditor={isEditor}
            isFullscreen={isFullscreen}
            showCanvasTitle={isFullscreen}
            sectionLinkBasePath={`/documents/${documentId}`}
            widthMode={contentWidth}
            contentEditRequestToken={contentEditRequestToken}
            onToggleFullscreen={isFullscreen ? navigateToDetail : navigateToFullscreen}
            highlightAnchor={highlightText}
            onRemovedSectionsChange={handleRemovedSectionsChange}
          />
        )}

        {activeTab === 'details' && (
          <>
            {isEditing ? (
              <EditForm
                document={document}
                onSave={updateDocument}
                onCancel={() => setIsEditing(false)}
                isLoading={isUpdatingDocument}
                canEditVisibility={isManager}
                initialCompanyIds={assignedCompanies.map((c) => c.id)}
              />
            ) : (
              <DocumentDetailsView
                document={document}
                isEditor={isEditor}
                canAssignCompanies={isManager}
                showCompanySelector={showCompanySelector}
                onToggleCompanySelector={toggleCompanySelector}
                assignedCompanies={assignedCompanies}
                assignmentDraftIds={assignmentDraftCompanyIds}
                hasUnsavedAssignmentChanges={hasUnsavedAssignmentChanges}
                audienceAccessPreview={audienceAccessPreview}
                onAssignmentDraftChange={updateAssignmentDraft}
                onSaveAssignmentDraft={saveAssignmentDraft}
                onDiscardAssignmentDraft={discardAssignmentDraft}
                isAssigningCompanies={isAssigningCompanies}
                onRemoveCompany={removeCompany}
                isRemovingCompany={isRemovingCompany}
                onSaveTags={(tags) => updateDocument({ tags: tags.join(', ') })}
                isSavingTags={isUpdatingDocument || isArchivingDocument}
                reviewHistoryItems={reviewHistoryItems}
              />
            )}
          </>
        )}

        {activeTab === 'versions' && (
          <Suspense
            fallback={
              <div className="surface-card rounded-2xl p-6">
                <p className="body-copy">Loading versions...</p>
              </div>
            }
          >
            <VersionsSection documentId={documentId} isEditor={isEditor} />
          </Suspense>
        )}

        {activeTab === 'attachments' && (
          <Suspense
            fallback={
              <div className="surface-card rounded-2xl p-6">
                <p className="body-copy">Loading attachments...</p>
              </div>
            }
          >
            <AttachmentsSection documentId={documentId} isEditor={isEditor} />
          </Suspense>
        )}



        <ReviewSubmitModal
          isOpen={showSubmitReview}
          documentId={documentId}
          documentTitle={document.title}
          message={submitMessage}
          onMessageChange={setSubmitMessage}
          onClose={closeSubmitReview}
          onSubmit={submitReview}
          isSubmitting={isSubmittingReview}
          errorMessage={submitReviewErrorMessage}
        />

        {showHelp && (
          <HelpPanel isEditor={isEditor} onClose={() => setShowHelp(false)} />
        )}

        {showRemovedSections && (
          <RemovedSectionsPanel
            removedSections={removedSections}
            onRestore={(section) => {
              restoreSectionRef.current(section)
            }}
            onClose={() => setShowRemovedSections(false)}
          />
        )}
      </div>
    </div>
  )
}
