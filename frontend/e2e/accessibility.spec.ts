/**
 * Y2-029: Accessibility test for public pages
 * Run axe-core on PublicHomePage, PublicDocumentsPage, PublicDocumentPage — zero critical violations.
 */
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const PUBLIC_PAGES = [
  { name: 'PublicHomePage', path: '/public' },
  { name: 'PublicDocumentsPage', path: '/public/documents' },
]

test.describe('Y2-029: Accessibility — public pages', () => {
  for (const { name, path } of PUBLIC_PAGES) {
    test(`${name} has no critical accessibility violations`, async ({ page }) => {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      const critical = results.violations.filter(
        (v) => v.impact === 'critical',
      )

      if (critical.length > 0) {
        const summary = critical.map(
          (v) => `[${v.id}] ${v.description} (${v.nodes.length} instance(s))`,
        )
        console.error('Critical violations found:', summary)
      }

      expect(critical).toHaveLength(0)
    })
  }

  test('PublicDocumentPage has no critical accessibility violations', async ({
    page,
  }) => {
    // Navigate to documents list first, then click the first document link
    await page.goto('/public/documents')
    await page.waitForLoadState('networkidle')

    const firstDocLink = page.locator('a[href*="/public/documents/"]').first()
    const hasDocLink = (await firstDocLink.count()) > 0

    if (hasDocLink) {
      await firstDocLink.click()
      await page.waitForLoadState('networkidle')

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      const critical = results.violations.filter(
        (v) => v.impact === 'critical',
      )
      expect(critical).toHaveLength(0)
    } else {
      // No public documents exist — skip gracefully
      test.skip()
    }
  })
})
