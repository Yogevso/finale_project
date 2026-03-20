import type { ReadingWidth } from '@/lib/readingWidth'
import { Minimize2 } from 'lucide-react'

interface FullscreenTopBarProps {
  isFullscreen: boolean
  documentTitle: string
  contentWidth: ReadingWidth
  onExitFullscreen: () => void
  onSetReadingWidth: () => void
  onSetFluidWidth: () => void
  wrapperClassName?: string
}

export function FullscreenTopBar({
  isFullscreen,
  documentTitle,
  contentWidth,
  onExitFullscreen,
  onSetReadingWidth,
  onSetFluidWidth,
  wrapperClassName,
}: FullscreenTopBarProps) {
  const topBarButtonClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 text-white transition-colors hover:bg-white/20'
  const widthToggleClassName =
    'table-action-btn rounded-full border text-xs transition-colors'

  if (!isFullscreen) {
    return null
  }

  return (
    <div
      className={`document-detail-fullscreen-topbar sticky top-0 z-30 flex items-center justify-between gap-4 bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 py-3 text-white shadow-lg ${
        wrapperClassName ?? '-mx-6 px-6 md:-mx-10 md:px-10 lg:-mx-14 lg:px-14'
      }`}
    >
      <button
        type="button"
        onClick={onExitFullscreen}
        className={topBarButtonClassName}
        title="Toggle fullscreen (F)"
      >
        <Minimize2 className="w-4 h-4" />
        Exit Fullscreen
      </button>
      <div className="card-title flex-1 truncate text-center !text-white">{documentTitle}</div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onSetReadingWidth}
          className={`${widthToggleClassName} ${
            contentWidth === 'reading'
              ? 'border-white bg-white text-sky-900'
              : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
          }`}
          title="Reading width"
        >
          Reading width
        </button>
        <button
          type="button"
          onClick={onSetFluidWidth}
          className={`${widthToggleClassName} ${
            contentWidth === 'fluid'
              ? 'border-white bg-white text-sky-900'
              : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
          }`}
          title="Full width"
        >
          Full width
        </button>
      </div>
    </div>
  )
}
