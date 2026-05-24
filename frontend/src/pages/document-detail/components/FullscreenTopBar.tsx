import { useEffect, useState } from 'react'
import type { ReadingWidth } from '@/lib/readingWidth'
import { Minimize2 } from 'lucide-react'

interface FullscreenTopBarProps {
  isFullscreen: boolean
  documentTitle: string
  contentWidth: ReadingWidth
  onExitFullscreen: () => void
  onSetReadingWidth: () => void
  onSetFluidWidth: () => void
  onToggleViewMode?: () => void
  viewModeLabel?: string
  wrapperClassName?: string
  isRevamp?: boolean
}

export function FullscreenTopBar({
  isFullscreen,
  documentTitle,
  contentWidth,
  onExitFullscreen,
  onSetReadingWidth,
  onSetFluidWidth,
  onToggleViewMode,
  viewModeLabel,
  wrapperClassName,
  isRevamp = true,
}: FullscreenTopBarProps) {
  const [isCondensed, setIsCondensed] = useState(false)

  useEffect(() => {
    if (!isFullscreen || !isRevamp) {
      setIsCondensed(false)
      return
    }

    const onScroll = () => {
      setIsCondensed(window.scrollY > 24)
    }

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [isFullscreen, isRevamp])

  const topBarButtonClassName =
    'table-action-btn inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 text-white transition-colors hover:bg-white/20'
  const widthToggleClassName = 'table-action-btn rounded-full border text-xs transition-colors'

  if (!isFullscreen) {
    return null
  }

  if (!isRevamp) {
    return (
      <div
        className={`document-detail-fullscreen-topbar z-30 flex items-center justify-between gap-4 bg-gradient-to-l from-blue-700 via-blue-600 to-blue-500 py-3 text-white shadow-lg ${
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
                ? 'border-white bg-white text-blue-900'
                : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
            }`}
            title="Reading width"
          >
            Reading width
          </button>
          {onToggleViewMode ? (
            <button
              type="button"
              onClick={onToggleViewMode}
              className="table-action-btn rounded-full border border-white bg-white px-3 text-xs font-semibold text-blue-900 shadow-sm transition-colors hover:bg-blue-50"
              title={viewModeLabel}
            >
              {viewModeLabel ?? 'Switch View'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={onSetFluidWidth}
            className={`${widthToggleClassName} ${
              contentWidth === 'fluid'
                ? 'border-white bg-white text-blue-900'
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

  return (
    <div
      className={`document-detail-fullscreen-topbar z-40 grid grid-cols-[auto,1fr,auto] items-center gap-3 rounded-2xl border border-blue-300/45 bg-blue-700/95 px-4 text-white shadow-[0_14px_34px_-20px_rgba(0,57,125,0.9)] backdrop-blur-xl transition-all duration-200 ${
        isCondensed ? 'py-2' : 'py-3'
      } ${wrapperClassName ?? ''}`}
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
      <div className="card-title hidden truncate text-center !text-white md:block">{documentTitle}</div>
      <div className="flex items-center justify-end gap-2">
        {onToggleViewMode ? (
          <button
            type="button"
            onClick={onToggleViewMode}
            className="table-action-btn rounded-full border border-white bg-white px-3 text-xs font-semibold text-slate-900 shadow-sm transition-colors hover:bg-slate-100"
            title={viewModeLabel}
          >
            {viewModeLabel ?? 'Switch View'}
          </button>
        ) : null}
        <button
          type="button"
          onClick={onSetReadingWidth}
          className={`${widthToggleClassName} ${
            contentWidth === 'reading'
              ? 'border-white bg-white text-slate-900'
              : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
          }`}
          title="Reading width"
        >
          <span className="md:hidden">Reading</span>
          <span className="hidden md:inline">Reading width</span>
        </button>
        <button
          type="button"
          onClick={onSetFluidWidth}
          className={`${widthToggleClassName} ${
            contentWidth === 'fluid'
              ? 'border-white bg-white text-slate-900'
              : 'border-white/30 bg-white/10 text-white hover:bg-white/20'
          }`}
          title="Full width"
        >
          <span className="md:hidden">Full</span>
          <span className="hidden md:inline">Full width</span>
        </button>
      </div>
      <span
        className="pointer-events-none col-span-3 mt-1 block h-px bg-gradient-to-r from-transparent via-blue-100/55 to-transparent"
        aria-hidden="true"
      />
    </div>
  )
}
