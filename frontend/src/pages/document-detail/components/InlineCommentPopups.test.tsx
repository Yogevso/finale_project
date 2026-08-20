import { render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { InlineCommentPopups } from '@/pages/document-detail/components/InlineCommentPopups'
import type { CommentPopupState } from '@/pages/document-detail/hooks/useInlineComments'

const POPUP_WIDTH = 320
const POPUP_HEIGHT = 300
const VIEWPORT_WIDTH = 1024
const VIEWPORT_HEIGHT = 768

const originalGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect

/** jsdom reports a zero-sized box, so the popup needs a realistic one to be clamped against. */
function stubPopupBox() {
  HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect(this: HTMLElement) {
    if (this.classList.contains('inline-comment-popup')) {
      return {
        width: POPUP_WIDTH,
        height: POPUP_HEIGHT,
        top: 0,
        left: 0,
        right: POPUP_WIDTH,
        bottom: POPUP_HEIGHT,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      } as DOMRect
    }
    return originalGetBoundingClientRect.call(this)
  }
}

function renderPopup(commentPopup: Partial<CommentPopupState>) {
  stubPopupBox()
  window.innerWidth = VIEWPORT_WIDTH
  window.innerHeight = VIEWPORT_HEIGHT

  render(
    <InlineCommentPopups
      hasUser
      selectionPopup={{ show: false, x: 0, y: 0, text: '', anchorId: '' }}
      commentPopup={{
        show: true,
        x: 500,
        y: 200,
        text: 'selected sentence',
        anchorId: 'intro',
        ...commentPopup,
      }}
      commentText=""
      isPrivateComment={false}
      isSubmittingComment={false}
      topOffset={0}
      onOpenCommentForm={() => undefined}
      onCloseCommentPopup={() => undefined}
      onCommentTextChange={() => undefined}
      onPrivateCommentChange={() => undefined}
      onSubmitComment={() => undefined}
    />,
  )

  const popup = document.querySelector<HTMLElement>('.inline-comment-popup')
  if (!popup) {
    throw new Error('comment popup was not rendered')
  }
  return popup
}

afterEach(() => {
  HTMLElement.prototype.getBoundingClientRect = originalGetBoundingClientRect
})

describe('InlineCommentPopups placement', () => {
  it('sits just below the selected text', () => {
    const popup = renderPopup({ anchorTop: 100, anchorBottom: 140 })

    expect(popup.style.top).toBe('152px')
    expect(popup.style.left).toBe('500px')
  })

  it('stays inside the viewport when the selection is near the bottom', () => {
    // y is what the hook's legacy `selection.y + 60` nudge produces for this selection,
    // and on its own it pushed the card's lower half past the bottom edge.
    const popup = renderPopup({ y: 750, anchorTop: 700, anchorBottom: 720 })

    const top = Number.parseFloat(popup.style.top)
    // Flipped above the selection rather than running off the bottom edge.
    expect(top + POPUP_HEIGHT).toBeLessThanOrEqual(VIEWPORT_HEIGHT)
    expect(top).toBe(388)
  })

  it('honours the top offset instead of hiding under a fullscreen bar', () => {
    stubPopupBox()
    window.innerWidth = VIEWPORT_WIDTH
    window.innerHeight = VIEWPORT_HEIGHT

    render(
      <InlineCommentPopups
        hasUser
        selectionPopup={{ show: false, x: 0, y: 0, text: '', anchorId: '' }}
        commentPopup={{
          show: true,
          x: 500,
          y: 0,
          text: 'selected sentence',
          anchorId: 'intro',
          anchorTop: 0,
          anchorBottom: 5,
        }}
        commentText=""
        isPrivateComment={false}
        isSubmittingComment={false}
        topOffset={76}
        onOpenCommentForm={() => undefined}
        onCloseCommentPopup={() => undefined}
        onCommentTextChange={() => undefined}
        onPrivateCommentChange={() => undefined}
        onSubmitComment={() => undefined}
      />,
    )

    const popup = document.querySelector<HTMLElement>('.inline-comment-popup')
    expect(Number.parseFloat(popup?.style.top ?? '0')).toBeGreaterThanOrEqual(76)
  })

  it('keeps the card on screen near the right edge and aims the arrow at the selection', () => {
    const popup = renderPopup({ x: 1010, anchorTop: 100, anchorBottom: 140 })

    // Clamped so the full 320px card is visible: 1024 - 12 margin - 160 half-width.
    expect(popup.style.left).toBe('852px')

    const arrow = popup.querySelector<HTMLElement>('[style*="translateX"]')
    // The card moved left, so the arrow shifts right to stay over the selection.
    expect(arrow?.style.transform).toContain('140px')
  })
})
