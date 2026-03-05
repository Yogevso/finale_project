import { expect, test, type Page } from '@playwright/test'

import { loginByApi } from './helpers/auth'

type Credentials = {
  username: string
  password: string
}

const E2E_BYPASS_HEADERS = { 'x-e2e-test': '1' }

async function ensureAdminUser(page: Page, credentials: Credentials) {
  const response = await page.request.post('/api/v1/auth/register', {
    headers: E2E_BYPASS_HEADERS,
    data: {
      email: `${credentials.username}@example.com`,
      username: credentials.username,
      full_name: 'Concurrent Visibility Admin',
      password: credentials.password,
      role: 'system_admin',
    },
    failOnStatusCode: false,
  })
  if (response.status() === 201) {
    return
  }
  if (response.status() === 400) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string }
    if ((payload.detail ?? '').toLowerCase().includes('already registered')) {
      return
    }
  }
  throw new Error(`Failed to provision E2E admin user (${response.status()}).`)
}

async function loginAsAdmin(page: Page, credentials: Credentials) {
  await loginByApi(page, credentials, /\/(dashboard|documents)/, '/dashboard')
}

async function resolveDocumentPathForConcurrencyTest(page: Page): Promise<string | null> {
  const accessToken = await page.evaluate(() =>
    window.localStorage.getItem('token') ?? window.localStorage.getItem('access_token'),
  )
  if (!accessToken) {
    throw new Error('Missing access token after login; cannot resolve E2E document.')
  }

  const response = await page.request.get('/api/v1/documents', {
    headers: {
      ...E2E_BYPASS_HEADERS,
      Authorization: `Bearer ${accessToken}`,
    },
    failOnStatusCode: false,
  })
  if (!response.ok()) {
    throw new Error(`Failed to query documents for concurrency test (${response.status()}).`)
  }

  const payload = (await response.json()) as { items?: Array<{ id: number }> }
  const firstDocumentId = payload.items?.[0]?.id
  if (!firstDocumentId) {
    return null
  }
  return `/documents/${firstDocumentId}`
}

async function openDetailsEditMode(page: Page) {
  await page.getByRole('button', { name: /^details$/i }).click()
  await page.getByRole('button', { name: /edit details/i }).click()
  await expect(page.locator('select[name="visibility"]')).toBeVisible()
}

async function prepareVisibilityChangeToPublic(page: Page) {
  await openDetailsEditMode(page)
  await page.locator('select[name="visibility"]').selectOption('public')
}

async function submitVisibilityChange(page: Page, reason: string) {
  await page.getByRole('button', { name: /save changes/i }).click()
  const reasonInput = page.getByTestId('visibility-change-reason')
  await expect(reasonInput).toBeVisible()
  await reasonInput.fill(reason)
  await page.getByRole('button', { name: /confirm change/i }).click()
}

test.describe('Concurrent visibility changes', () => {
  test('shows conflict feedback in the second tab when visibility is updated concurrently', async ({ browser }) => {
    const credentials: Credentials = {
      username: `e2e_admin_${Date.now()}`,
      password: 'admin12345',
    }
    const contextOne = await browser.newContext()
    const contextTwo = await browser.newContext()
    const pageOne = await contextOne.newPage()
    const pageTwo = await contextTwo.newPage()

    try {
      await ensureAdminUser(pageOne, credentials)
      await loginAsAdmin(pageOne, credentials)
      const documentPath = await resolveDocumentPathForConcurrencyTest(pageOne)
      if (!documentPath) {
        test.skip(true, 'No documents available for concurrency visibility test.')
        return
      }

      await loginAsAdmin(pageTwo, credentials)
      await pageTwo.goto(documentPath)
      await expect(pageTwo).toHaveURL(/\/documents\/\d+/)
      await prepareVisibilityChangeToPublic(pageTwo)

      await pageOne.goto(documentPath)
      await expect(pageOne).toHaveURL(/\/documents\/\d+/)
      await prepareVisibilityChangeToPublic(pageOne)
      await submitVisibilityChange(pageOne, 'First tab applies visibility change')
      await expect(pageOne.getByRole('button', { name: /edit details/i })).toBeVisible()

      const conflictDialogPromise = pageTwo.waitForEvent('dialog')
      await submitVisibilityChange(pageTwo, 'Second tab tries stale visibility update')
      const conflictDialog = await conflictDialogPromise
      expect(conflictDialog.message()).toMatch(/write conflict detected/i)
      await conflictDialog.accept()
    } finally {
      await contextOne.close()
      await contextTwo.close()
    }
  })
})
