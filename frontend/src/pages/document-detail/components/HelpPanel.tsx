import {
  CalendarDays,
  CheckCircle,
  Clock,
  Download,
  FileText,
  HelpCircle,
  Maximize2,
  Send,
  Star,
  Trash2,
  X,
  XCircle,
} from 'lucide-react'

interface HelpPanelProps {
  isEditor: boolean
  onClose: () => void
}

const helpItems = [
  {
    icon: Star,
    label: 'Add to My Activities',
    description:
      'Bookmark this document so it appears in your personal activity feed. You can find all bookmarked documents on your dashboard.',
  },
  {
    icon: FileText,
    label: 'Generate Transcript',
    description:
      "Opens your browser's print dialog so you can save or print a clean copy of the document content.",
  },
  {
    icon: Download,
    label: 'Download',
    description:
      'Download the document in different formats. Available formats depend on the original file type: PDF is always available; Word and PowerPoint are offered when the source matches.',
  },
  {
    icon: CalendarDays,
    label: 'Export iCal',
    description:
      "Downloads an iCal (.ics) file for the document's due date so you can add it to your calendar app.",
    editorOnly: false,
  },
  {
    icon: Maximize2,
    label: 'Fullscreen',
    description:
      'Expands the document to fill the entire screen for distraction-free reading. Press F or click Exit Fullscreen to return.',
  },
  {
    icon: Send,
    label: 'Submit for Review',
    description:
      'Sends the current document version to reviewers for approval. Depending on the status, the label changes to "Resubmit for Review" or "Submit New Review".',
    editorOnly: true,
  },
  {
    icon: Clock,
    label: 'Pending Review',
    description:
      'Indicates the document is currently being reviewed. You can cancel the review at any time without losing content.',
    editorOnly: true,
  },
  {
    icon: XCircle,
    label: 'Cancel Review',
    description:
      'Cancels the active review request. The document returns to its previous state and all content is preserved.',
    editorOnly: true,
  },
  {
    icon: CheckCircle,
    label: 'Approved',
    description:
      'The document has been approved by a reviewer and is ready to be published.',
    editorOnly: true,
  },
  {
    icon: FileText,
    label: 'Edit Document',
    description:
      'Opens the document editor where you can modify sections, add new content, or rearrange the structure.',
    editorOnly: true,
  },
  {
    icon: Trash2,
    label: 'Removed Sections',
    description:
      'Opens a panel showing all sections you have deleted. Removed sections are kept here until a review is submitted and approved, allowing you to restore them if needed.',
    editorOnly: true,
  },
  {
    icon: HelpCircle,
    label: 'Help',
    description: 'Opens this help panel explaining all header actions.',
  },
]

export function HelpPanel({ isEditor, onClose }: HelpPanelProps) {
  const visibleItems = helpItems.filter((item) => !item.editorOnly || isEditor)

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close help"
      />
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900">Document Actions Guide</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close help"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <ul className="space-y-5">
            {visibleItems.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.label} className="flex gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">{item.label}</p>
                    <p className="mt-0.5 text-sm leading-relaxed text-slate-500">
                      {item.description}
                    </p>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </>
  )
}
