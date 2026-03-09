import { History, RotateCcw, Trash2 } from 'lucide-react'
import { formatDate } from '@/lib/dateUtils'

interface DraftRecoveryNoticeProps {
  savedAt: string
  onRestore: () => void
  onDismiss: () => void
}

export default function DraftRecoveryNotice({
  savedAt,
  onRestore,
  onDismiss,
}: DraftRecoveryNoticeProps) {
  return (
    <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <History className="mt-0.5 h-5 w-5 text-amber-700" />
          <div>
            <p className="font-semibold">Restore unsaved changes?</p>
            <p className="mt-1 text-amber-800">
              A local draft from {formatDate(savedAt)} was recovered for this editor.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onRestore}
            className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            <RotateCcw className="h-4 w-4" />
            Restore draft
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100"
          >
            <Trash2 className="h-4 w-4" />
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}
