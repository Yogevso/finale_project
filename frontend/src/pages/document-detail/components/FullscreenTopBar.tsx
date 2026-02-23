import type { ReadingWidth } from '@/lib/readingWidth'
import { Minimize2 } from 'lucide-react'

interface FullscreenTopBarProps {
  isFullscreen: boolean
  documentTitle: string
  contentWidth: ReadingWidth
  onExitFullscreen: () => void
  onSetReadingWidth: () => void
  onSetFluidWidth: () => void
}

export function FullscreenTopBar({
  isFullscreen,
  documentTitle,
  contentWidth,
  onExitFullscreen,
  onSetReadingWidth,
  onSetFluidWidth,
}: FullscreenTopBarProps) {
  if (!isFullscreen) {
    return null
  }

  return (
    <div className="sticky top-0 z-30 -mx-6 md:-mx-10 lg:-mx-14 px-6 md:px-10 lg:px-14 py-3 bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white shadow-lg flex items-center justify-between gap-4">
      <button
        onClick={onExitFullscreen}
        className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/15 rounded-lg hover:bg-white/25 transition-colors"
      >
        <Minimize2 className="w-4 h-4" />
        Exit Fullscreen
      </button>
      <div className="flex-1 text-center font-display font-semibold truncate">{documentTitle}</div>
      <div className="flex items-center gap-2">
        <button
          onClick={onSetReadingWidth}
          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
            contentWidth === 'reading'
              ? 'bg-white text-sky-900 border-white'
              : 'bg-white/10 text-white border-white/30 hover:bg-white/20'
          }`}
          title="Reading width"
        >
          Reading width
        </button>
        <button
          onClick={onSetFluidWidth}
          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
            contentWidth === 'fluid'
              ? 'bg-white text-sky-900 border-white'
              : 'bg-white/10 text-white border-white/30 hover:bg-white/20'
          }`}
          title="Full width"
        >
          Full width
        </button>
      </div>
    </div>
  )
}
