import { expect, test } from '@playwright/test'

import { loginByApi } from './helpers/auth'

const ADMIN = { username: 'admin', password: 'admin123' }

test.describe('Mobile navigation', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('opens hamburger menu and navigates to documents', async ({ page }) => {
    await loginByApi(page, ADMIN, /\/dashboard/, '/dashboard')
    await page.goto('/dashboard')

    const hamburgerButton = page.getByRole('button', { name: /open navigation menu/i })
    await expect(hamburgerButton).toBeVisible()

    await hamburgerButton.click()
    await expect(page.getByRole('button', { name: /close navigation menu/i })).toBeVisible()

    const documentsLink = page
      .locator('a[href="/documents"]')
      .filter({ hasText: 'Documents' })
      .first()
    await expect(documentsLink).toBeVisible()
    await documentsLink.click()

    await expect(page).toHaveURL(/\/documents/)
  })
})
