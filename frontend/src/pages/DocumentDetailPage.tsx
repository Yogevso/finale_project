import { lazy, Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Joyride from 'react-joyride'
import { DocumentPreview } from '@/pages/document-detail/DocumentPreview'
import { EditForm } from '@/pages/document-detail/EditForm'
import { DocumentDetailsView } from '@/pages/document-detail/components/DocumentDetailsView'
import { DocumentHeaderCard } from '@/pages/document-detail/components/DocumentHeaderCard'
import { DocumentTabs } from '@/pages/document-detail/components/DocumentTabs'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'
import { ReviewSubmitModal } from '@/pages/document-detail/components/ReviewSubmitModal'
import { useDocumentDetailPageState } from '@/pages/document-detail/hooks/useDocumentDetailPageState'
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
  const [pendingPrint, setPendingPrint] = useState(false)
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
  } = useDocumentDetailPageState()

  useEffect(() => {
    setReadingTimeMinutes(null)
  }, [documentId])

  useEffect(() => {
    if (!pendingPrint || activeTab !== 'preview') {
      return
    }

    const timer = window.setTimeout(() => {
      window.print()
      setPendingPrint(false)
    }, 0)

    return () => window.clearTimeout(timer)
  }, [activeTab, pendingPrint])

  const tabCounts = {
    versions: document?.versions_count ?? 0,
    attachments: document?.attachments_count ?? attachments.length,
  }

  const handlePrint = () => {
    if (activeTab === 'preview') {
      window.print()
      return
    }

    if (setActiveTab('preview')) {
      setPendingPrint(true)
    }
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
          onBackToDocuments={navigateToDocuments}
          onEnterFullscreen={navigateToFullscreen}
          onExitFullscreen={navigateToDetail}
          onPrint={handlePrint}
          onExportCalendar={document.due_date ? exportCalendar : undefined}
          onOpenSubmitReview={openSubmitReview}
          onEditAction={handleEditAction}
          onArchive={handleArchive}
          onRestore={handleRestore}
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
          documentTitle={document.title}
          message={submitMessage}
          onMessageChange={setSubmitMessage}
          onClose={closeSubmitReview}
          onSubmit={submitReview}
          isSubmitting={isSubmittingReview}
          errorMessage={submitReviewErrorMessage}
        />
      </div>
    </div>
  )
}
