import { expect, test } from '@playwright/test'

const RESET_TOKEN = 'known-reset-token'
const RESET_USERNAME = 'reset-flow-user'
const RESET_EMAIL = 'reset-flow-user@example.com'
const RESET_PASSWORD = 'ResetPass123!'

test.describe('Password reset flow', () => {
  test('requests reset, sets new password, and logs in', async ({ page }) => {
    await page.route('**/api/v1/auth/forgot-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'If an account exists for that identifier, reset instructions will be sent.',
          reset_token: RESET_TOKEN,
        }),
      })
    })

    await page.route('**/api/v1/auth/reset-password', async (route) => {
      const payload = route.request().postDataJSON() as {
        token?: string
        new_password?: string
      }
      const validPayload = payload.token === RESET_TOKEN && payload.new_password === RESET_PASSWORD
      await route.fulfill({
        status: validPayload ? 200 : 400,
        contentType: 'application/json',
        body: JSON.stringify(
          validPayload
            ? { message: 'Password has been reset successfully' }
            : { detail: 'Invalid reset payload' },
        ),
      })
    })

    await page.route('**/api/v1/auth/login', async (route) => {
      const payload = route.request().postDataJSON() as {
        username?: string
        password?: string
      }
      const validCredentials =
        payload.username === RESET_USERNAME && payload.password === RESET_PASSWORD
      await route.fulfill({
        status: validCredentials ? 200 : 401,
        contentType: 'application/json',
        body: JSON.stringify(
          validCredentials
            ? {
                access_token: 'mock-access-token',
                refresh_token: 'mock-refresh-token',
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
          id: 1001,
          email: RESET_EMAIL,
          username: RESET_USERNAME,
          full_name: 'Reset Flow User',
          role: 'editor',
          is_active: true,
          permissions: [],
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
    await page.getByRole('button', { name: /forgot password\?/i }).click()
    await page.getByPlaceholder('you@example.com').fill(RESET_EMAIL)
    await page.getByRole('button', { name: /send reset link/i }).click()
    await expect(
      page.getByText(/if an account exists for that identifier, reset instructions will be sent/i),
    ).toBeVisible()

    await page.goto(`/reset-password?token=${RESET_TOKEN}`)
    await page.getByLabel(/new password/i).fill(RESET_PASSWORD)
    await page.getByLabel(/confirm password/i).fill(RESET_PASSWORD)
    await page.getByRole('button', { name: /^reset password$/i }).click()

    await expect(page.getByText(/password reset successful/i)).toBeVisible()
    await expect(page).toHaveURL(/\/login/)

    await page.getByLabel(/username/i).fill(RESET_USERNAME)
    await page.getByLabel(/^password$/i).fill(RESET_PASSWORD)
    await page.getByRole('button', { name: /^sign in$/i }).click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
  })
})
