import { expect, test } from '@playwright/test'
import { getApiAuthHeaders, loginByApi } from './helpers/auth'
import { createDocumentViaApi } from './helpers/documents'

const ADMIN = { username: 'admin', password: 'admin123' }

test('bookmarking a document shows it inside the dashboard favorites section', async ({ page }) => {
  const documentRecord = await createDocumentViaApi(page, ADMIN, {
    title: `Bookmark Doc ${Date.now()}`,
    status: 'active',
  })

  await loginByApi(page, ADMIN, /\/(dashboard|documents)/, '/dashboard')
  await page.goto(`/documents/${documentRecord.id}`)

  const bookmarkButton = page.getByTitle('Add bookmark')
  await expect(bookmarkButton).toBeVisible()
  await bookmarkButton.click()
  await expect
    .poll(async () => {
      const headers = await getApiAuthHeaders(page, ADMIN)
      const response = await page.request.get(
        `/api/v1/engagement/bookmarks/${documentRecord.id}/status`,
        { headers },
      )
      const payload = (await response.json()) as { is_bookmarked: boolean }
      return payload.is_bookmarked
    })
    .toBe(true)

  await page.goto('/dashboard')

  const bookmarksCard = page.locator('.surface-card').filter({
    has: page.getByRole('heading', { name: /my bookmarks/i }),
  }).first()
  await expect(bookmarksCard.getByText(documentRecord.title)).toBeVisible()
})
