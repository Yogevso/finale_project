import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FullscreenTopBar } from '@/pages/document-detail/components/FullscreenTopBar'

describe('FullscreenTopBar', () => {
  it('renders exit and width controls in reading mode', async () => {
    const user = userEvent.setup()
    const onExitFullscreen = vi.fn()
    const onSetReadingWidth = vi.fn()
    const onSetFluidWidth = vi.fn()

    render(
      <FullscreenTopBar
        isFullscreen
        documentTitle="Quarterly Rollout"
        contentWidth="reading"
        onExitFullscreen={onExitFullscreen}
        onSetReadingWidth={onSetReadingWidth}
        onSetFluidWidth={onSetFluidWidth}
      />,
    )

    expect(screen.getByRole('button', { name: /exit fullscreen/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reading width/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /full width/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /exit fullscreen/i }))
    await user.click(screen.getByRole('button', { name: /reading width/i }))

    expect(onExitFullscreen).toHaveBeenCalledTimes(1)
    expect(onSetReadingWidth).toHaveBeenCalledTimes(1)
  })

  it('renders exit and width controls in fluid mode', async () => {
    const user = userEvent.setup()
    const onSetFluidWidth = vi.fn()

    render(
      <FullscreenTopBar
        isFullscreen
        documentTitle="Quarterly Rollout"
        contentWidth="fluid"
        onExitFullscreen={vi.fn()}
        onSetReadingWidth={vi.fn()}
        onSetFluidWidth={onSetFluidWidth}
      />,
    )

    await user.click(screen.getByRole('button', { name: /full width/i }))

    expect(screen.getByRole('button', { name: /exit fullscreen/i })).toBeInTheDocument()
    expect(onSetFluidWidth).toHaveBeenCalledTimes(1)
  })
})
