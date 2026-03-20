import { expect, test } from '@playwright/test';

import { adminLogin } from '../helpers/auth';

test.describe('Phase 10 UX states', () => {
  test('support page shows a loading skeleton while tickets are pending', async ({ page }) => {
    await page.route('**/api/v1/support/tickets**', async (route) => {
      await page.waitForTimeout(12000);
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
    await expect(page.getByRole('status', { name: /loading/i }).first()).toBeVisible();
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('support page shows the shared error state on fetch failure', async ({ page }) => {
    await page.route('**/api/v1/support/tickets**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'boom' }),
      });
    });

    await adminLogin(page, '/support', /\/support/);
    await expect(page.getByText(/tickets could not be loaded/i)).toBeVisible();
  });

  test('canned responses page shows the shared empty state', async ({ page }) => {
    await page.route('**/api/v1/support/canned-responses**', async (route) => {
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

    await adminLogin(page, '/support/canned-responses', /\/support\/canned-responses/);
    await expect(page.getByText(/no canned responses yet/i)).toBeVisible();
  });

  test('notifications page shows the shared empty state', async ({ page }) => {
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
    await expect(page.getByText(/no notifications yet/i)).toBeVisible();
  });
});
