import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ImageLightbox from './ImageLightbox'

describe('ImageLightbox', () => {
  it('supports keyboard navigation for gallery images', () => {
    const onClose = vi.fn()
    const onPrevious = vi.fn()
    const onNext = vi.fn()

    render(
      <ImageLightbox
        src="/image.png"
        alt="Preview image"
        onClose={onClose}
        onPrevious={onPrevious}
        onNext={onNext}
      />,
    )

    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    fireEvent.keyDown(window, { key: 'Escape' })

    expect(onPrevious).toHaveBeenCalledTimes(1)
    expect(onNext).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('focuses the close control instead of the backdrop when opened', async () => {
    render(<ImageLightbox src="/image.png" alt="Preview image" onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /close image preview/i })[1]).toHaveFocus()
    })
  })
})
