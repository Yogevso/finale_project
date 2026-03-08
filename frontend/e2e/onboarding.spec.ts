import { expect, test } from '@playwright/test'

const MANAGER = { username: 'manager-onboarding', password: 'ManagerPass123!' }

test.describe('Onboarding checklist', () => {
  test('shows checklist, updates progress, and dismisses after completion', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      const payload = route.request().postDataJSON() as {
        username?: string
        password?: string
      }
      const validCredentials =
        payload.username === MANAGER.username && payload.password === MANAGER.password
      await route.fulfill({
        status: validCredentials ? 200 : 401,
        contentType: 'application/json',
        body: JSON.stringify(
          validCredentials
            ? {
                access_token: 'mock-manager-token',
                refresh_token: 'mock-manager-refresh',
                token_type: 'bearer',
              }
            : { detail: 'Invalid credentials' },
        ),
      })
    })

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 2002,
          email: 'manager-onboarding@example.com',
          username: MANAGER.username,
          full_name: 'Onboarding Manager',
          role: 'manager',
          is_active: true,
          permissions: ['manage_users'],
          created_at: '2026-03-08T00:00:00Z',
          updated_at: '2026-03-08T00:00:00Z',
        }),
      })
    })

    await page.route('**/api/v1/documents/stats', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 0,
          published: 0,
          approved: 0,
          draft: 0,
        }),
      })
    })

    await page.route('**/api/v1/documents**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 5,
          pages: 0,
        }),
      })
    })

    await page.goto('/login')
    await page.getByLabel(/username/i).fill(MANAGER.username)
    await page.getByLabel(/^password$/i).fill(MANAGER.password)
    await page.getByRole('button', { name: /^sign in$/i }).click()
    await expect(page).toHaveURL(/\/dashboard/)

    const checklistHeading = page.getByRole('heading', { name: /onboarding checklist/i })
    await expect(checklistHeading).toBeVisible()

    await page.locator('a[href="/profile"]').filter({ hasText: 'Go to step' }).first().click()
    await expect(page).toHaveURL(/\/profile/)

    await page.goto('/dashboard')
    const setupProfileCompleteButton = page.getByRole('button', {
      name: /mark set up profile complete/i,
    })
    await setupProfileCompleteButton.click()
    await expect(page.getByText('1/3 completed')).toBeVisible()

    const remainingStepButtons = page.locator('button[aria-label^="Mark "]')
    while ((await remainingStepButtons.count()) > 0) {
      await remainingStepButtons.first().click()
    }

    await expect(page.getByRole('heading', { name: /onboarding checklist/i })).toHaveCount(0)
  })
})
