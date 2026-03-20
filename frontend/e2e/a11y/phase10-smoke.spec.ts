import AxeBuilder from '@axe-core/playwright';
import { test } from '@playwright/test';

import { adminLogin } from '../helpers/auth';
import { assertNoBlockingViolations, waitForAppReady } from '../helpers/phase10';

test.describe('Phase 10 accessibility smoke', () => {
  test('login page has no serious or critical axe violations', async ({ page }) => {
    await page.goto('/login');
    await waitForAppReady(page, page.locator('form'));

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    assertNoBlockingViolations(results.violations);
  });

  test('public search empty state has no serious or critical axe violations', async ({ page }) => {
    await page.route('**/api/v1/public/categories', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.route('**/api/v1/public/search**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          query: 'phase10',
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        }),
      });
    });

    await page.goto('/search?q=phase10');
    await waitForAppReady(page, page.getByText(/no results found/i));

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    assertNoBlockingViolations(results.violations);
  });

  test('support empty state has no serious or critical axe violations', async ({ page }) => {
    await page.route('**/api/v1/support/tickets**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
        }),
      });
    });

    await adminLogin(page, '/support', /\/support/);
    await waitForAppReady(page, page.getByText(/no tickets found/i));

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    assertNoBlockingViolations(results.violations);
  });
});
