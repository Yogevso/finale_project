import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface ImageLightboxProps {
  src: string
  alt?: string
  title?: string
  onClose: () => void
}

export default function ImageLightbox({ src, alt, title, onClose }: ImageLightboxProps) {
  const { containerRef, handleKeyDown: trapKeyDown } = useFocusTrap(onClose)

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

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
      onClick={onClose}
      onKeyDown={trapKeyDown}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
        aria-label="Close image preview"
      >
        <X className="h-5 w-5" />
      </button>
      <div className="max-h-full max-w-full" onClick={(event) => event.stopPropagation()}>
        <img
          src={src}
          alt={alt || title || 'Expanded document image'}
          className="max-h-[88vh] max-w-[92vw] rounded-xl object-contain shadow-2xl"
        />
        {(title || alt) && (
          <p className="mt-3 text-center text-sm text-slate-200">{title || alt}</p>
        )}
      </div>
    </div>,
    document.body,
  )
}
