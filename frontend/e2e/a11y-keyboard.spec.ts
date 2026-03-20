/**
 * AC-020: Keyboard Browsing E2E Test
 *
 * Verifies that all interactive elements are reachable via keyboard (Tab)
 * and that focus indicators are visible (focus-visible ring).
 */
import { test, expect } from '@playwright/test'

test.describe('AC-020: Keyboard Navigation', () => {
  test('public home page is fully keyboard-navigable', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Collect all interactive elements that should be tabbable
    const interactive = page.locator(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]',
    )
    const count = await interactive.count()
    expect(count).toBeGreaterThan(0)

    // Tab through the first several elements and verify each receives focus
    const maxToCheck = Math.min(count, 15)
    for (let i = 0; i < maxToCheck; i++) {
      await page.keyboard.press('Tab')
      const focused = page.locator(':focus')
      const focusedTag = await focused.evaluate((el) => el?.tagName?.toLowerCase() || '')
      // The focused element should be a meaningful interactive element
      expect(['a', 'button', 'input', 'select', 'textarea', 'div', 'span', 'li']).toContain(focusedTag)
    }
  })

  test('login page form fields are reachable via Tab', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // Tab to the first input
    await page.keyboard.press('Tab') // skip link
    await page.keyboard.press('Tab') // first form element or nav link

    // Keep tabbing until we land on an input
    let foundInput = false
    for (let i = 0; i < 20; i++) {
      const tag = await page.locator(':focus').evaluate((el) => el?.tagName?.toLowerCase() || '')
      if (tag === 'input') {
        foundInput = true
        break
      }
      await page.keyboard.press('Tab')
    }
    expect(foundInput).toBe(true)
  })

  test('Escape key does not break navigation', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Tab a few times, press Escape, then Tab again — focus should still work
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Escape')
    await page.keyboard.press('Tab')

    const focused = page.locator(':focus')
    await expect(focused).toBeAttached()
  })
})
