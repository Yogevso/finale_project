import { expect, test } from '@playwright/test';

import { adminLogin } from '../helpers/auth';
import { waitForAppReady } from '../helpers/phase10';

test.describe('Phase 10 visual smoke', () => {
  test('login page matches the baseline', async ({ page }) => {
    await page.goto('/login');
    await waitForAppReady(page, page.locator('form'));

    await expect(page).toHaveScreenshot('login-page.png', {
      animations: 'disabled',
      fullPage: true,
    });
  });

  test('public search empty state matches the baseline', async ({ page }) => {
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

    await expect(page).toHaveScreenshot('public-search-empty.png', {
      animations: 'disabled',
      fullPage: true,
    });
  });

  test('support empty state matches the baseline', async ({ page }) => {
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

    await expect(page).toHaveScreenshot('support-empty-state.png', {
      animations: 'disabled',
      fullPage: true,
    });
  });

  test('notifications empty state matches the baseline', async ({ page }) => {
    await page.route('**/api/v1/notifications**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          unread_count: 0,
        }),
      });
    });

    await adminLogin(page, '/notifications', /\/notifications/);
    await waitForAppReady(page, page.getByText(/no notifications yet/i));

    await expect(page).toHaveScreenshot('notifications-empty-state.png', {
      animations: 'disabled',
      fullPage: true,
    });
  });
});
