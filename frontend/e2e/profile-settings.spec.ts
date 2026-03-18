import { expect, test } from '@playwright/test'

import { loginByApi } from './helpers/auth'

const ADMIN = { username: 'admin', password: 'admin123' }

test.describe('Profile settings', () => {
  test('updates full name and persists after reload', async ({ page }) => {
    await loginByApi(page, ADMIN, /\/dashboard/, '/dashboard')
    await page.goto('/profile')
    await expect(page).toHaveURL(/\/profile/)

    const fullNameInput = page.locator('#main-content input[type="text"]').first()
    const saveButton = page.getByRole('button', { name: /save profile/i })

    const originalName = await fullNameInput.inputValue()
    const updatedName = `${originalName} QA`

    await fullNameInput.fill(updatedName)
    await saveButton.click()
    await expect(page.getByText(/profile updated/i)).toBeVisible()

    await page.reload()
    await expect(page.locator('#main-content input[type="text"]').first()).toHaveValue(updatedName)

    await page.locator('#main-content input[type="text"]').first().fill(originalName)
    await saveButton.click()
    await expect(page.getByText(/profile updated/i)).toBeVisible()
  })
})
