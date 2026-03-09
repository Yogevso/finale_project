import { expect, test } from '@playwright/test'
import { loginByApi } from './helpers/auth'
import { createDocumentViaApi, createVersionViaApi } from './helpers/documents'

const ADMIN = { username: 'admin', password: 'admin123' }

test('in-document search shows match counts and moves focus between occurrences', async ({ page }) => {
  const documentRecord = await createDocumentViaApi(page, ADMIN, {
    title: `Search Doc ${Date.now()}`,
  })
  await createVersionViaApi(page, ADMIN, documentRecord.id, {
    changes_summary: 'Seed in-document search coverage',
    content: '<h1>Search Demo</h1><p>Needle Alpha</p><p>Context paragraph</p><p>Needle Beta</p>',
  })

  await loginByApi(page, ADMIN, /\/(dashboard|documents)/, '/dashboard')
  await page.goto(`/documents/${documentRecord.id}/fullscreen`)

  const searchInput = page.getByRole('textbox', { name: /search in document/i })
  await expect(searchInput).toBeVisible()
  await searchInput.fill('Needle')

  await expect(page.getByText('1 of 2')).toBeVisible()
  await expect(page.locator('mark.doc-highlight--active').locator('xpath=ancestor::p[1]')).toContainText(
    'Needle Alpha',
  )

  await page.getByTitle('Next match').click()
  await expect(page.getByText('2 of 2')).toBeVisible()
  await expect(page.locator('mark.doc-highlight--active').locator('xpath=ancestor::p[1]')).toContainText(
    'Needle Beta',
  )

  await page.getByTitle('Previous match').click()
  await expect(page.getByText('1 of 2')).toBeVisible()
  await expect(page.locator('mark.doc-highlight--active').locator('xpath=ancestor::p[1]')).toContainText(
    'Needle Alpha',
  )
})
