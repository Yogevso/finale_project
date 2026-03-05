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

    await page.getByRole('button', { name: 'Export' }).click()
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Export as CSV' }).click(),
    ])
    expect(download.suggestedFilename()).toContain('analytics-overview-')
    expect(download.suggestedFilename()).toContain('.csv')
  })
})
