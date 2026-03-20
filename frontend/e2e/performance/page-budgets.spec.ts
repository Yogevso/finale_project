import { expect, test, type Page } from '@playwright/test';

import { adminLogin } from '../helpers/auth';
import { waitForAppReady } from '../helpers/phase10';

const DEV_SERVER_FCP_BUDGET_MS = Number(process.env.PHASE10_FCP_BUDGET_MS || '6000');
const DEV_SERVER_INTERACTIVE_BUDGET_MS = Number(process.env.PHASE10_INTERACTIVE_BUDGET_MS || '6000');

async function collectNavigationMetrics(page: Page) {
  return page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    const paints = performance.getEntriesByType('paint');
    const firstContentfulPaint =
      paints.find((entry) => entry.name === 'first-contentful-paint')?.startTime ?? null;

    return {
      domInteractive: navigation?.domInteractive ?? null,
      domContentLoaded: navigation?.domContentLoadedEventEnd ?? null,
      loadEventEnd: navigation?.loadEventEnd ?? null,
      firstContentfulPaint,
    };
  });
}

async function warmAndMeasure(page: Page, path: string, readyTarget: Parameters<typeof waitForAppReady>[1]) {
  await page.goto(path);
  await waitForAppReady(page, readyTarget);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await waitForAppReady(page, readyTarget);
  return collectNavigationMetrics(page);
}

test.describe('Phase 10 performance budgets', () => {
  test('login page stays within the interactive budget', async ({ page }) => {
    const metrics = await warmAndMeasure(page, '/login', page.locator('form'));

    expect(metrics.firstContentfulPaint).not.toBeNull();
    expect(
      metrics.firstContentfulPaint!,
      `Expected FCP under ${DEV_SERVER_FCP_BUDGET_MS}ms on the warmed dev server`,
    ).toBeLessThan(DEV_SERVER_FCP_BUDGET_MS);
    expect(
      metrics.domInteractive!,
      `Expected interactive time under ${DEV_SERVER_INTERACTIVE_BUDGET_MS}ms on the warmed dev server`,
    ).toBeLessThan(DEV_SERVER_INTERACTIVE_BUDGET_MS);
  });

  test('dashboard stays within the interactive budget', async ({ page }) => {
    await adminLogin(page, '/dashboard', /\/dashboard/);
    await waitForAppReady(page, page.locator('h1').filter({ hasText: 'Dashboard' }));
    const metrics = await collectNavigationMetrics(page);

    expect(
      metrics.domContentLoaded!,
      `Expected DOMContentLoaded under ${DEV_SERVER_INTERACTIVE_BUDGET_MS}ms on the warmed dev server`,
    ).toBeLessThan(DEV_SERVER_INTERACTIVE_BUDGET_MS);
    expect(
      metrics.domInteractive!,
      `Expected interactive time under ${DEV_SERVER_INTERACTIVE_BUDGET_MS}ms on the warmed dev server`,
    ).toBeLessThan(DEV_SERVER_INTERACTIVE_BUDGET_MS);
  });
});
