import { useState, type ImgHTMLAttributes, type KeyboardEvent, type MouseEvent } from 'react'
import ImageLightbox from '@/components/ImageLightbox'
import OptimizedImage from '@/components/OptimizedImage'

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

  const handleClick = (event: MouseEvent<HTMLImageElement>) => {
    props.onClick?.(event)
    if (event.defaultPrevented) {
      return
    }

    event.preventDefault()
    event.stopPropagation()
    handleOpen()
  }

  const width = props.width ?? 1600
  const height = props.height ?? 900

  return (
    <>
      <OptimizedImage
        {...props}
        alt={alt}
        blurPlaceholder
        className={[props.className, 'cursor-zoom-in'].filter(Boolean).join(' ')}
        containerClassName="block"
        height={height}
        responsiveWidths={[480, 768, 1200, 1600]}
        aria-haspopup="dialog"
        role="button"
        tabIndex={0}
        width={width}
        onClick={handleClick}
        onKeyDown={(event) => {
          props.onKeyDown?.(event)
          if (!event.defaultPrevented) {
            handleKeyDown(event)
          }
        }}
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
