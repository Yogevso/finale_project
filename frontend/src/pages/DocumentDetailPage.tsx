import { lazy, Suspense } from 'react'
import { DocumentPreview } from '@/pages/document-detail/DocumentPreview'
import { EditForm } from '@/pages/document-detail/EditForm'
import { DocumentDetailsView } from '@/pages/document-detail/components/DocumentDetailsView'
import { DocumentHeaderCard } from '@/pages/document-detail/components/DocumentHeaderCard'
import { DocumentTabs } from '@/pages/document-detail/components/DocumentTabs'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'
import { ReviewSubmitModal } from '@/pages/document-detail/components/ReviewSubmitModal'
import { useDocumentDetailPageState } from '@/pages/document-detail/hooks/useDocumentDetailPageState'
import EngagementBar from '@/components/EngagementBar'
import NotFoundState from '@/components/NotFoundState'

const VersionsSection = lazy(() => import('@/components/VersionsSection'))
const AttachmentsSection = lazy(() => import('@/components/AttachmentsSection'))
const CommentsSection = lazy(() => import('@/components/CommentsSection'))

export default function DocumentDetailPage() {
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
    pendingAnchor,
    clearPendingAnchor,
    contentEditRequestToken,
    showCompanySelector,
    toggleCompanySelector,
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
    reviewHistoryItems,
    navigateToDocuments,
    navigateToFullscreen,
    navigateToDetail,
    handleDelete,
    handleEditAction,
    updateDocument,
    isUpdatingDocument,
    assignCompanies,
    isAssigningCompanies,
    removeCompany,
    isRemovingCompany,
    isSubmittingReview,
  } = useDocumentDetailPageState()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600"></div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <NotFoundState
        title="Document Not Found"
        description="This document may not exist or you may not have access."
      />
    )
  }

  return (
    <div className={`${isFullscreen ? 'min-h-screen bg-slate-50 px-6 md:px-10 lg:px-14 py-6' : ''}`}>
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
          documentTitle={document.title}
          documentNumber={document.document_number}
          isFullscreen={isFullscreen}
          isEditor={isEditor}
          documentStatus={document.status}
          activeTab={activeTab}
          isEditing={isEditing}
          onBackToDocuments={navigateToDocuments}
          onEnterFullscreen={navigateToFullscreen}
          onExitFullscreen={navigateToDetail}
          onOpenSubmitReview={openSubmitReview}
          onEditAction={handleEditAction}
          onDelete={handleDelete}
        />

        <EngagementBar
          documentId={documentId}
          scrollProgress={activeTab === 'preview' ? scrollProgress : undefined}
        />

        <DocumentTabs activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === 'preview' && (
          <DocumentPreview
            documentId={documentId}
            attachments={attachments}
            documentTitle={document.title}
            onScrollProgress={handleScrollProgress}
            isEditor={isEditor}
            widthMode={contentWidth}
            contentEditRequestToken={contentEditRequestToken}
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
              />
            ) : (
              <DocumentDetailsView
                document={document}
                isEditor={isEditor}
                showCompanySelector={showCompanySelector}
                onToggleCompanySelector={toggleCompanySelector}
                assignedCompanies={assignedCompanies}
                onAssignCompanies={assignCompanies}
                isAssigningCompanies={isAssigningCompanies}
                onRemoveCompany={removeCompany}
                isRemovingCompany={isRemovingCompany}
                reviewHistoryItems={reviewHistoryItems}
              />
            )}
          </>
        )}

        {activeTab === 'versions' && (
          <Suspense fallback={<div className="surface-card rounded-2xl p-6">Loading versions...</div>}>
            <VersionsSection documentId={documentId} isEditor={isEditor} />
          </Suspense>
        )}

        {activeTab === 'attachments' && (
          <Suspense
            fallback={<div className="surface-card rounded-2xl p-6">Loading attachments...</div>}
          >
            <AttachmentsSection documentId={documentId} isEditor={isEditor} />
          </Suspense>
        )}

        {activeTab === 'comments' && (
          <Suspense fallback={<div className="surface-card rounded-2xl p-6">Loading comments...</div>}>
            <CommentsSection
              documentId={documentId}
              pendingAnchor={pendingAnchor}
              onClearAnchor={clearPendingAnchor}
            />
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
