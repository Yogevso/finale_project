/**
 * AC-023: Accessibility CI Regression Test
 *
 * A compact "smoke" suite that runs axe-core on critical pages to catch
 * regressions.  Keep this test fast so it can run in CI on every push.
 */
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const CRITICAL_ROUTES = [
  { name: 'Home', path: '/' },
  { name: 'Login', path: '/login' },
  { name: 'Help', path: '/help' },
  { name: 'Browse', path: '/browse' },
  { name: 'Accessibility', path: '/accessibility' },
]

test.describe('AC-023: Accessibility CI Regression Suite', () => {
  for (const { name, path } of CRITICAL_ROUTES) {
    test(`[regression] ${name} — no WCAG 2.1 AA violations`, async ({ page }) => {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      const blocking = results.violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious',
      )

      if (blocking.length > 0) {
        const summary = blocking
          .map(
            (v) =>
              `[${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} instance(s))`,
          )
          .join('\n')
        expect(blocking.length, `WCAG violations on ${name}:\n${summary}`).toBe(0)
      }
    })
  }

  test('[regression] skip-nav link present on home page', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const skipLink = page.locator('a[href="#main-content"]')
    await expect(skipLink.first()).toBeAttached()

    const mainContent = page.locator('#main-content')
    await expect(mainContent).toBeAttached()
  })

  test('[regression] ARIA landmarks are correct', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Should have at least one main landmark
    const main = page.locator('main, [role="main"]')
    await expect(main.first()).toBeAttached()

    // Should have at least one navigation landmark
    const nav = page.locator('nav, [role="navigation"]')
    await expect(nav.first()).toBeAttached()
  })

  test('[regression] no images without alt text on public pages', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Find all img elements
    const images = page.locator('img')
    const count = await images.count()

    for (let i = 0; i < count; i++) {
      const img = images.nth(i)
      const alt = await img.getAttribute('alt')
      const role = await img.getAttribute('role')
      // Images must have alt text OR be marked presentational
      const isAccessible = alt !== null || role === 'presentation' || role === 'none'
      expect(isAccessible, `Image at index ${i} is missing alt text`).toBe(true)
    }
  })

  test('[regression] form inputs have associated labels', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    const inputs = page.locator('input:not([type="hidden"]):not([type="submit"])')
    const count = await inputs.count()

    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i)
      const id = await input.getAttribute('id')
      const ariaLabel = await input.getAttribute('aria-label')
      const ariaLabelledBy = await input.getAttribute('aria-labelledby')
      const placeholder = await input.getAttribute('placeholder')

      // Input must be identifiable by screen readers via at least one method
      const hasLabel =
        (id && (await page.locator(`label[for="${id}"]`).count()) > 0) ||
        !!ariaLabel ||
        !!ariaLabelledBy ||
        !!placeholder

      expect(hasLabel, `Input at index ${i} has no accessible label`).toBe(true)
    }
  })
})
