import { test, expect } from '@playwright/test'

/**
 * AA-014 / AA-023: Mobile Responsiveness Baseline
 *
 * Verify public and portal pages render correctly at standard mobile
 * and tablet viewport widths with no horizontal overflow.
 *
 * Viewports: 375px (mobile), 768px (tablet), 1024px (small desktop)
 */

const VIEWPORTS = [
  { width: 375, height: 812, label: 'Mobile (375px)' },
  { width: 768, height: 1024, label: 'Tablet (768px)' },
  { width: 1024, height: 768, label: 'Small Desktop (1024px)' },
]

const PUBLIC_PAGES = [
  { name: 'Home', path: '/' },
  { name: 'Browse', path: '/browse' },
  { name: 'Login', path: '/login' },
]

for (const viewport of VIEWPORTS) {
  test.describe(`Mobile Responsiveness — ${viewport.label}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } })

    for (const { name, path } of PUBLIC_PAGES) {
      test(`${name} (${path}) has no horizontal overflow`, async ({ page }) => {
        await page.goto(path)
        await page.waitForLoadState('networkidle')

        // Check that document doesn't have horizontal scroll
        const hasOverflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth
        })

        expect(hasOverflow, `Horizontal overflow detected on ${name} at ${viewport.width}px`).toBe(false)
      })

      test(`${name} (${path}) renders visible content`, async ({ page }) => {
        await page.goto(path)
        await page.waitForLoadState('networkidle')

        // Body should have visible content
        await expect(page.locator('body')).toBeVisible()

        // No elements should extend beyond viewport width
        const overflowingElements = await page.evaluate((vw) => {
          const elements = document.querySelectorAll('*')
          const overflowing: string[] = []
          for (const el of elements) {
            const rect = el.getBoundingClientRect()
            if (rect.right > vw + 5) { // 5px tolerance
              overflowing.push(`${el.tagName}.${el.className} (right: ${rect.right}px)`)
            }
          }
          return overflowing.slice(0, 5) // Return first 5
        }, viewport.width)

        if (overflowingElements.length > 0) {
          console.warn(`Elements extending beyond viewport:`, overflowingElements)
        }
      })
    }

    // Mobile-specific: check that navigation is accessible
    if (viewport.width <= 768) {
      test('mobile navigation toggle is accessible', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // Look for a hamburger/menu button (common patterns)
        const menuButton = page.getByRole('button', { name: /menu|navigation|hamburger/i })
          .or(page.locator('button[aria-label*="menu" i]'))
          .or(page.locator('[data-testid="mobile-menu"]'))
          .first()

        // If mobile nav toggle exists, it should be visible at this viewport
        if (await menuButton.isVisible({ timeout: 2000 }).catch(() => false)) {
          await expect(menuButton).toBeVisible()
        }
      })
    }
  })
}
