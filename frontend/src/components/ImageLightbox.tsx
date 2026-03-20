import { useEffect, useId, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, ZoomIn, ZoomOut, RotateCcw, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { useFocusTrap } from '@/hooks/useAccessibility'
import OptimizedImage from '@/components/OptimizedImage'

interface ImageLightboxProps {
  src: string
  alt?: string
  title?: string
  onClose: () => void
  onPrevious?: () => void
  onNext?: () => void
}

export default function ImageLightbox({ src, alt, title, onClose, onPrevious, onNext }: ImageLightboxProps) {
  const descriptionId = useId()
  const { containerRef } = useFocusTrap(onClose)
  const [zoom, setZoom] = useState(1)
  const [imageLoaded, setImageLoaded] = useState(false)

  useEffect(() => {
    setImageLoaded(false)
    setZoom(1)
  }, [src])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      } else if (event.key === 'ArrowLeft' && onPrevious) {
        onPrevious()
      } else if (event.key === 'ArrowRight' && onNext) {
        onNext()
      } else if (event.key === '+' || event.key === '=') {
        setZoom((z) => Math.min(z + 0.25, 3))
      } else if (event.key === '-') {
        setZoom((z) => Math.max(z - 0.25, 0.5))
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, onPrevious, onNext])

  if (typeof document === 'undefined') {
    return null
  }

  return createPortal(
    <div
      ref={containerRef}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/90 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={alt || title || 'Image preview'}
      aria-describedby={title || alt ? descriptionId : undefined}
      tabIndex={-1}
    >
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close image preview"
        tabIndex={-1}
      />
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
        aria-label="Close image preview"
      >
        <X className="h-5 w-5" />
      </button>

      {/* Zoom controls */}
      <div className="absolute left-4 top-4 flex items-center gap-1">
        <button
          type="button"
          onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
          aria-label="Zoom in"
        >
          <ZoomIn className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
          aria-label="Zoom out"
        >
          <ZoomOut className="h-5 w-5" />
        </button>
        {zoom !== 1 && (
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
            aria-label="Reset zoom"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
        <span className="ml-1 text-xs text-white/70">{Math.round(zoom * 100)}%</span>
      </div>

      {/* Previous / Next gallery nav */}
      {onPrevious && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onPrevious() }}
          className="absolute left-4 top-1/2 -translate-y-1/2 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
          aria-label="Previous image"
          aria-keyshortcuts="ArrowLeft"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}
      {onNext && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onNext() }}
          className="absolute right-4 top-1/2 -translate-y-1/2 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
          aria-label="Next image"
          aria-keyshortcuts="ArrowRight"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}

      <div className="relative z-10 max-h-full max-w-full">
        {!imageLoaded && (
          <div className="flex items-center justify-center p-12" role="status" aria-live="polite" aria-label="Loading image preview">
            <Loader2 className="h-8 w-8 animate-spin text-white/60" />
          </div>
        )}
        <OptimizedImage
          src={src}
          alt={alt || title || 'Expanded document image'}
          blurPlaceholder
          className="max-h-[88vh] max-w-[92vw] rounded-xl object-contain shadow-2xl transition-transform duration-200"
          containerClassName="block"
          height={900}
          responsiveWidths={[960, 1440, 1920, 2560]}
          sizes="92vw"
          style={{ transform: `scale(${zoom})`, display: imageLoaded ? undefined : 'none' }}
          width={1600}
          onLoad={() => setImageLoaded(true)}
        />
        {(title || alt) && (
          <p id={descriptionId} className="mt-3 text-center text-sm text-slate-200">{title || alt}</p>
        )}
      </div>
    </div>,
    document.body,
  )
}
