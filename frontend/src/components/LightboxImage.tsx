import { useState, type ImgHTMLAttributes, type KeyboardEvent } from 'react'
import ImageLightbox from '@/components/ImageLightbox'

export default function LightboxImage(props: ImgHTMLAttributes<HTMLImageElement>) {
  const [isOpen, setIsOpen] = useState(false)
  const src = typeof props.src === 'string' ? props.src : ''
  const alt = typeof props.alt === 'string' ? props.alt : undefined
  const title = typeof props.title === 'string' ? props.title : undefined

  const handleOpen = () => {
    if (!src) {
      return
    }
    setIsOpen(true)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLImageElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleOpen()
    }
  }

  return (
    <>
      <img
        {...props}
        alt={alt}
        decoding="async"
        loading="lazy"
        className={[props.className, 'cursor-zoom-in'].filter(Boolean).join(' ')}
        aria-haspopup="dialog"
        role="button"
        tabIndex={0}
        onClick={(event) => {
          event.preventDefault()
          event.stopPropagation()
          handleOpen()
        }}
        onKeyDown={handleKeyDown}
      />
      {isOpen && src && (
        <ImageLightbox
          src={src}
          alt={alt}
          title={title}
          onClose={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
