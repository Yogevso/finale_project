import { expect, test, type Page } from '@playwright/test'

import { loginByApi } from './helpers/auth'

const MANAGER = { username: 'manager', password: 'manager123' }

async function loginAsManager(page: Page) {
  await loginByApi(page, MANAGER, /\/(analytics|dashboard|documents)/, '/analytics')
}

test.describe('Audit Analytics', () => {
  test('manager can view audience breakdown and export CSV', async ({ page }) => {
    await loginAsManager(page)
    await page.goto('/analytics')

    await expect(page.getByText('Analytics Dashboard')).toBeVisible()
    await expect(page.getByTestId('audience-segmentation-chart')).toBeVisible()
    await expect(page.getByTestId('audience-type-internal')).toBeVisible()
    await expect(page.getByTestId('audience-type-company')).toBeVisible()
    await expect(page.getByTestId('audience-type-public')).toBeVisible()

    const exportResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/analytics/export/csv'),
    )
    await page.getByRole('button', { name: 'Export CSV' }).click()
    const exportResponse = await exportResponsePromise

    expect(exportResponse.ok()).toBeTruthy()
    const contentDisposition = exportResponse.headers()['content-disposition'] ?? ''
    expect(contentDisposition).toContain('.csv')
  })
})
