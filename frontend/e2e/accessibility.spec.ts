/**
 * Y2-029 + AA-012/AA-022: WCAG 2.1 AA Accessibility Audit
 *
 * Run axe-core on key public and portal pages.
 * Asserts zero critical AND serious violations (WCAG 2.1 AA standard).
 */
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const PUBLIC_PAGES = [
  { name: 'PublicHomePage', path: '/' },
  { name: 'PublicBrowse', path: '/browse' },
  { name: 'LoginPage', path: '/login' },
  { name: 'PublicDocumentsPage', path: '/public/documents' },
  { name: 'PublicHomeLegacy', path: '/public' },
]

function assertNoCriticalOrSerious(
  violations: { impact?: string | null; id: string; description: string; nodes: unknown[] }[],
) {
  const blocking = violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious',
  )
  if (blocking.length > 0) {
    const summary = blocking
      .map(
        (v) =>
          `[${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} instance(s))`,
      )
      .join('\n')
    expect(
      blocking.length,
      `Critical/serious a11y violations:\n${summary}`,
    ).toBe(0)
  }
}

test.describe('AA-012/AA-022: Accessibility — WCAG 2.1 AA audit (public pages)', () => {
  for (const { name, path } of PUBLIC_PAGES) {
    test(`${name} (${path}) has no critical/serious a11y violations`, async ({
      page,
    }) => {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      assertNoCriticalOrSerious(results.violations)
    })
  }

  test('PublicDocumentPage has no critical/serious a11y violations', async ({
    page,
  }) => {
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

      assertNoCriticalOrSerious(results.violations)
    } else {
      // No public documents exist — skip gracefully
      test.skip()
    }
  })
})
