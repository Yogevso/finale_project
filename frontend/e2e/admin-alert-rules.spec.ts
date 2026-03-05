import { expect, test, type Page } from '@playwright/test'

import { loginByApi } from './helpers/auth'

const SYSTEM_ADMIN = { username: 'sysadmin', password: 'sysadmin123' }

async function loginAsSystemAdmin(page: Page) {
  await loginByApi(page, SYSTEM_ADMIN, /\/(admin\/system-setup|dashboard|documents)/, '/admin/system-setup')
}

test.describe('Audience Alert Rules', () => {
  test('system admin can create and delete an audience alert rule', async ({ page }) => {
    await loginAsSystemAdmin(page)
    await page.goto('/admin/system-setup')

    await expect(page.getByTestId('audience-alert-rules-section')).toBeVisible()

    const uniqueMetric = `visibility_changes_test_${Date.now()}`
    await page.getByTestId('audience-alert-rule-metric').fill(uniqueMetric)
    await page.getByTestId('audience-alert-rule-threshold').fill('7')
    await page.getByTestId('audience-alert-rule-window').fill('30')

    await page.getByTestId('audience-alert-rule-create').click()
    const createdRow = page.getByTestId('audience-alert-rule-list').locator('li', {
      hasText: uniqueMetric,
    })
    await expect(createdRow).toBeVisible()

    await createdRow.getByRole('button', { name: 'Delete' }).click()
    await expect(createdRow).toHaveCount(0)
  })
})
