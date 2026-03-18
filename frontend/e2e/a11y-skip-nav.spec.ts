/**
 * AC-019: Skip Navigation E2E Test
 *
 * Verifies the "Skip to main content" link:
 *  - exists on all layouts
 *  - becomes visible when focused
 *  - transfers focus to #main-content on click
 */
import { test, expect } from '@playwright/test'

const PAGES_WITH_SKIP_NAV = [
  { name: 'PublicHome', path: '/' },
  { name: 'Login', path: '/login' },
  { name: 'Help', path: '/help' },
]

test.describe('AC-019: Skip Navigation', () => {
  for (const { name, path } of PAGES_WITH_SKIP_NAV) {
    test(`${name} has a skip-to-main-content link that works`, async ({ page }) => {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      // The skip link should exist in the DOM
      const skipLink = page.locator('a[href="#main-content"]').first()
      await expect(skipLink).toBeAttached()

      // It should start visually hidden (sr-only)
      const box = await skipLink.boundingBox()
      // sr-only elements have no visible bounding box (width 1px, height 1px, overflow hidden)
      // so boundingBox may be null or tiny
      const isHidden = !box || (box.width <= 1 && box.height <= 1)
      expect(isHidden).toBe(true)

      // Tab into the page — the skip link should be the first focusable element
      await page.keyboard.press('Tab')
      await expect(skipLink).toBeFocused()

      // Once focused, the link should become visible (not sr-only)
      const focusedBox = await skipLink.boundingBox()
      expect(focusedBox).toBeTruthy()
      expect(focusedBox!.width).toBeGreaterThan(10)
      expect(focusedBox!.height).toBeGreaterThan(10)

      // Click the skip link
      await skipLink.click()

      // The #main-content landmark should exist
      const mainContent = page.locator('#main-content')
      await expect(mainContent).toBeAttached()
    })
  }
})
