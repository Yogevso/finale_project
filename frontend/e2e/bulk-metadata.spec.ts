import { expect, test } from '@playwright/test'
import { loginByApi } from './helpers/auth'
import { createDocumentViaApi, searchDocumentsViaApi } from './helpers/documents'

const ADMIN = { username: 'admin', password: 'admin123' }
const MANAGER = { username: 'manager', password: 'manager123' }

test('bulk metadata edit updates category for three selected documents', async ({ page }) => {
  test.setTimeout(45000)
  const seedPrefix = `Bulk Metadata ${Date.now()}`
  const seededDocuments = await Promise.all([
    createDocumentViaApi(page, ADMIN, { title: `${seedPrefix} A`, category: 'Legacy' }),
    createDocumentViaApi(page, ADMIN, { title: `${seedPrefix} B`, category: 'Legacy' }),
    createDocumentViaApi(page, ADMIN, { title: `${seedPrefix} C`, category: 'Legacy' }),
  ])

  await loginByApi(page, MANAGER, /\/(dashboard|documents)/, '/dashboard')
  await page.goto('/documents')

  await page.getByPlaceholder('Search documents...').fill(seedPrefix)

  for (const documentRecord of seededDocuments) {
    await page.getByRole('checkbox', { name: `Select ${documentRecord.title}` }).check()
  }

  await expect(page.getByText('3 document(s) selected')).toBeVisible()

  const bulkEditButton = page.getByRole('button', { name: /bulk edit metadata/i })
  await expect(bulkEditButton).toBeVisible()
  await bulkEditButton.evaluate((button: HTMLButtonElement) => button.click())
  await page.getByPlaceholder('Leave blank to keep current value').fill('Compliance')
  const bulkUpdateResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/documents/bulk-metadata') &&
      response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: /apply changes/i }).click()
  const bulkUpdateResponse = await bulkUpdateResponsePromise
  expect(bulkUpdateResponse.ok()).toBeTruthy()

  await expect(page.getByText('3 document(s) selected')).not.toBeVisible({ timeout: 10000 })

  await expect
    .poll(async () => {
      const searchResults = await searchDocumentsViaApi(page, MANAGER, seedPrefix)
      const matchedDocuments = searchResults.items.filter((item) =>
        item.title.startsWith(seedPrefix),
      )

      return matchedDocuments.map((item) => item.category)
    })
    .toEqual(['Compliance', 'Compliance', 'Compliance'])
})
