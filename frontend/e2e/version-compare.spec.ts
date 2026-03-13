import { expect, test } from '@playwright/test'
import { loginByApi } from './helpers/auth'
import { createDocumentViaApi, createVersionViaApi } from './helpers/documents'

const ADMIN = { username: 'admin', password: 'admin123' }

test('version compare renders a side-by-side diff for two versions', async ({ page }) => {
  const documentRecord = await createDocumentViaApi(page, ADMIN, {
    title: `Compare Doc ${Date.now()}`,
  })
  await createVersionViaApi(page, ADMIN, documentRecord.id, {
    changes_summary: 'Initial draft',
    content: '<h1>Version Compare Demo</h1><p>Original rollout steps</p>',
  })
  await createVersionViaApi(page, ADMIN, documentRecord.id, {
    changes_summary: 'Updated rollout steps',
    bump_type: 'minor',
    content:
      '<h1>Version Compare Demo</h1><p>Updated rollout steps</p><p>Added verification checklist</p>',
  })

  await loginByApi(page, ADMIN, /\/(dashboard|documents)/, '/dashboard')
  await page.goto(`/documents/${documentRecord.id}/compare`)

  await expect(page.getByRole('heading', { name: new RegExp(`Compare versions for ${documentRecord.title}`) })).toBeVisible()
  await expect(page.getByText('Added verification checklist')).toBeVisible()
  await expect(page.getByText('Original rollout steps')).toBeVisible()
  await expect(page.getByText('Updated rollout steps')).toBeVisible()
  await expect(page.getByText('Changed').first()).toBeVisible()
})
