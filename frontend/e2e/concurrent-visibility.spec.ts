import { expect, test, type Page } from '@playwright/test'

import { loginByApi } from './helpers/auth'

type Credentials = {
  username: string
  password: string
}

const E2E_BYPASS_HEADERS = { 'x-e2e-test': '1' }
const ADMIN: Credentials = {
  username: 'admin',
  password: 'admin123',
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
  const reasonDialogVisible = await reasonInput
    .waitFor({ state: 'visible', timeout: 1000 })
    .then(() => true)
    .catch(() => false)

  if (!reasonDialogVisible) {
    return
  }

  await reasonInput.fill(reason)
  await page.getByRole('button', { name: /confirm change/i }).click()
  await expect(reasonInput).toBeHidden()
}

test.describe('Concurrent visibility changes', () => {
  test('shows conflict feedback in the second tab when visibility is updated concurrently', async ({ browser }) => {
    const contextOne = await browser.newContext()
    const contextTwo = await browser.newContext()
    const pageOne = await contextOne.newPage()
    const pageTwo = await contextTwo.newPage()

    try {
      await loginAsAdmin(pageOne, ADMIN)
      const documentPath = await resolveDocumentPathForConcurrencyTest(pageOne)
      if (!documentPath) {
        test.skip(true, 'No documents available for concurrency visibility test.')
        return
      }

      await loginAsAdmin(pageTwo, ADMIN)
      await pageTwo.goto(documentPath)
      await expect(pageTwo).toHaveURL(/\/documents\/\d+/)
      await prepareVisibilityChangeToPublic(pageTwo)

      await pageOne.goto(documentPath)
      await expect(pageOne).toHaveURL(/\/documents\/\d+/)
      await prepareVisibilityChangeToPublic(pageOne)
      await submitVisibilityChange(pageOne, 'First tab applies visibility change')

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
