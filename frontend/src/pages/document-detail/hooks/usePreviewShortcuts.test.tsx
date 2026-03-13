import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { usePreviewShortcuts } from './usePreviewShortcuts'

describe('usePreviewShortcuts', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('focuses the search input on slash and toggles fullscreen on f', () => {
    const searchInput = document.createElement('input')
    const focusMock = vi.spyOn(searchInput, 'focus')
    const selectMock = vi.spyOn(searchInput, 'select')
    document.body.appendChild(searchInput)

    const onToggleFullscreen = vi.fn()

    renderHook(() =>
      usePreviewShortcuts({
        searchInputRef: { current: searchInput },
        editingSection: null,
        showContentEditChooser: false,
        handleCloseCommentPopup: vi.fn(),
        handleCloseSectionEdit: vi.fn(),
        handleCloseContentEditChooser: vi.fn(),
        navigateBetweenSections: vi.fn(),
        onToggleFullscreen,
      }),
    )

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }))
    })

    expect(focusMock).toHaveBeenCalledTimes(1)
    expect(selectMock).toHaveBeenCalledTimes(1)

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'f', bubbles: true }))
    })

    expect(onToggleFullscreen).toHaveBeenCalledTimes(1)
  })

  it('navigates sections with j/k, closes overlays on escape, and ignores typing targets', () => {
    const searchInput = document.createElement('input')
    document.body.appendChild(searchInput)

    const handleCloseCommentPopup = vi.fn()
    const handleCloseSectionEdit = vi.fn()
    const handleCloseContentEditChooser = vi.fn()
    const navigateBetweenSections = vi.fn()

    renderHook(() =>
      usePreviewShortcuts({
        searchInputRef: { current: searchInput },
        editingSection: { id: 'intro' },
        showContentEditChooser: true,
        handleCloseCommentPopup,
        handleCloseSectionEdit,
        handleCloseContentEditChooser,
        navigateBetweenSections,
      }),
    )

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', bubbles: true }))
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', bubbles: true }))
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    })

    expect(navigateBetweenSections).toHaveBeenNthCalledWith(1, 1)
    expect(navigateBetweenSections).toHaveBeenNthCalledWith(2, -1)
    expect(handleCloseCommentPopup).toHaveBeenCalledTimes(1)
    expect(handleCloseSectionEdit).toHaveBeenCalledTimes(1)
    expect(handleCloseContentEditChooser).toHaveBeenCalledTimes(1)

    act(() => {
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', bubbles: true }))
    })

    expect(navigateBetweenSections).toHaveBeenCalledTimes(2)
  })
})
