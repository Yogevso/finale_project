import { useMemo, useState, type ImgHTMLAttributes } from 'react'

interface OptimizedImageProps extends ImgHTMLAttributes<HTMLImageElement> {
  blurPlaceholder?: boolean
  containerClassName?: string
  responsiveWidths?: number[]
}

function joinClasses(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ')
}

function toNumericDimension(value: ImgHTMLAttributes<HTMLImageElement>['width']) {
  if (typeof value === 'number') {
    return value
  }

  if (typeof value === 'string' && /^\d+$/.test(value)) {
    return Number(value)
  }

  return undefined
}

function buildResponsiveSrcSet(src: string, responsiveWidths?: number[]) {
  if (!responsiveWidths?.length || src.startsWith('blob:') || src.startsWith('data:')) {
    return undefined
  }

  const widths = [...new Set(responsiveWidths.filter((value) => value > 0))].sort((a, b) => a - b)
  if (widths.length === 0) {
    return undefined
  }

  // The current APIs mostly expose a single source URL. We still provide width-based
  // browser hints so the component is ready for multi-size image endpoints later.
  return widths.map((width) => `${src} ${width}w`).join(', ')
}

export default function OptimizedImage({
  alt,
  blurPlaceholder = false,
  className,
  containerClassName,
  decoding,
  height,
  loading,
  onError,
  onLoad,
  responsiveWidths,
  sizes,
  src,
  srcSet,
  width,
  ...rest
}: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)

  const resolvedSrc = typeof src === 'string' ? src : undefined
  const resolvedWidth = toNumericDimension(width)
  const resolvedHeight = toNumericDimension(height)

  const computedSrcSet = useMemo(() => {
    if (srcSet) {
      return srcSet
    }

    if (!resolvedSrc) {
      return undefined
    }

    return buildResponsiveSrcSet(resolvedSrc, responsiveWidths)
  }, [responsiveWidths, resolvedSrc, srcSet])

  const showBlurPlaceholder =
    blurPlaceholder && Boolean(resolvedSrc) && !isLoaded && !hasError

  return (
    <span
      className={joinClasses(
        'block',
        showBlurPlaceholder && 'relative overflow-hidden',
        containerClassName,
      )}
    >
      {showBlurPlaceholder ? (
        <span
          aria-hidden="true"
          className="absolute inset-0 z-0 scale-105 bg-cover bg-center blur-2xl transition-opacity duration-300"
          style={{ backgroundImage: `url("${resolvedSrc}")` }}
        />
      ) : null}
      <img
        {...rest}
        alt={alt}
        className={joinClasses(
          'relative z-10 transition-opacity duration-300',
          showBlurPlaceholder ? 'opacity-0' : 'opacity-100',
          className,
        )}
        decoding={decoding ?? 'async'}
        height={resolvedHeight ?? height}
        loading={loading ?? 'lazy'}
        sizes={computedSrcSet ? sizes ?? '100vw' : sizes}
        src={src}
        srcSet={computedSrcSet}
        width={resolvedWidth ?? width}
        onError={(event) => {
          setHasError(true)
          onError?.(event)
        }}
        onLoad={(event) => {
          setIsLoaded(true)
          onLoad?.(event)
        }}
      />
    </span>
  )
}
