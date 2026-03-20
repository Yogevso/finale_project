import { expect, test } from '@playwright/test';

import { adminLogin } from '../helpers/auth';
import { RESPONSIVE_VIEWPORTS, expectNoHorizontalOverflow, waitForAppReady } from '../helpers/phase10';

for (const viewport of RESPONSIVE_VIEWPORTS) {
  test.describe(`Phase 10 responsive coverage - ${viewport.label}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test('public home has no horizontal overflow', async ({ page }) => {
      await page.goto('/docs');
      await waitForAppReady(page, page.getByRole('heading', { name: /documentation library/i }));
      await expectNoHorizontalOverflow(page);
    });

    test('login page has no horizontal overflow', async ({ page }) => {
      await page.goto('/login');
      await waitForAppReady(page, page.locator('form'));
      await expectNoHorizontalOverflow(page);
    });

    test('dashboard has no horizontal overflow', async ({ page }) => {
      await adminLogin(page, '/dashboard', /\/dashboard/);
      await waitForAppReady(page, page.locator('h1').filter({ hasText: 'Dashboard' }));
      await expectNoHorizontalOverflow(page);
    });

    test('public search empty state stays within the viewport', async ({ page }) => {
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
      await expectNoHorizontalOverflow(page);
      await expect(page.getByRole('heading', { name: /search documents/i })).toBeVisible();
    });
  });
}
