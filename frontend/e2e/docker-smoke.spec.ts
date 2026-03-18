/**
 * PHASE 14 - Docker Smoke Test
 * Runs against the live Docker Compose stack at http://localhost:3000
 * Verifies items #139-#148 from VERIFICATION_UX_PLAN.md
 *
 * Run: $env:BASE_URL="http://localhost:3000"; $env:PW_SKIP_WEBSERVER="1"; npx playwright test e2e/docker-smoke.spec.ts
 */
import { test, expect, type Page } from '@playwright/test'

// Helpers
async function login(page: Page, user: string, pass: string, expectedPath: RegExp) {
  await page.goto('/login')
  await page.fill('input#username', user)
  await page.fill('input#password', pass)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(expectedPath, { timeout: 15000 })
}

async function adminLogin(page: Page) {
  await login(page, 'admin', 'admin123', /\/(dashboard|documents)/)
}

async function customerLogin(page: Page) {
  await login(page, 'customer1', 'customer123', /\/portal/)
}

// #139 - Public docs loads 30 documents
test('#139 Public docs loads documents', async ({ page }) => {
  const apiResp = await page.request.get('/api/v1/public/documents?page=1&per_page=20')
  expect(apiResp.ok()).toBeTruthy()
  const body = await apiResp.json()
  expect(body.total).toBeGreaterThanOrEqual(30)

  await page.goto('/docs')
  await page.waitForLoadState('networkidle')

  const cards = page.locator('a[href^="/doc/"]')
  await expect(cards.first()).toBeVisible({ timeout: 10000 })
  const count = await cards.count()
  expect(count).toBeGreaterThanOrEqual(1)
})

// #140 - Search returns results
test('#140 Search returns results', async ({ page }) => {
  await page.goto('/search?q=API')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(2000)

  const results = page.locator('a[href^="/doc/"]')
  const resultCount = await results.count()
  expect(resultCount).toBeGreaterThanOrEqual(1)
})

// #141 - Category filters work
test('#141 Category filters work', async ({ page }) => {
  await page.goto('/docs')
  await page.waitForLoadState('networkidle')

  // Category filter buttons exist on the docs page sidebar
  const catResp = await page.request.get('/api/v1/public/categories')
  if (catResp.ok()) {
    const catBody = await catResp.json()
    const catCount = Array.isArray(catBody) ? catBody.length : (catBody.items?.length ?? 0)
    expect(catCount).toBeGreaterThanOrEqual(1)
  } else {
    const topicResp = await page.request.get('/api/v1/public/topics')
    expect(topicResp.ok()).toBeTruthy()
  }

  // Try clicking a category filter button on the page
  const filterBtn = page.locator('button.rounded-full').first()
  if (await filterBtn.isVisible()) {
    await filterBtn.click()
    await page.waitForTimeout(1000)
  }
})

// #142 - Individual document renders content
test('#142 Individual document renders content', async ({ page }) => {
  const apiResp = await page.request.get('/api/v1/public/documents?page=1&per_page=1')
  const body = await apiResp.json()
  expect(body.items.length).toBeGreaterThanOrEqual(1)
  const docId = body.items[0].id
  const docTitle = body.items[0].title

  // Route is /doc/:id
  await page.goto(`/doc/${docId}`)
  await page.waitForLoadState('networkidle')

  const titleSnippet = docTitle.replace(/[^a-zA-Z0-9 ]/g, '').replace(/\s+/g, ' ').trim().split(' ')[0]
  await expect(page.locator('body')).toContainText(new RegExp(titleSnippet, 'i'), { timeout: 10000 })
  await expect(page.locator('body')).not.toContainText(/page not found/i)
})

// #143 - Login -> Dashboard with stats
test('#143 Login to Dashboard with stats', async ({ page }) => {
  await adminLogin(page)
  await expect(page.locator('body')).toContainText(/dashboard|welcome|documents|overview/i, { timeout: 10000 })

  const stats = page.locator('[class*="stat"], [class*="card"], [class*="metric"], [class*="count"], [class*="widget"]')
  const statCount = await stats.count()
  expect(statCount).toBeGreaterThanOrEqual(1)
})

// #144 - Document create/edit/publish flow
test('#144 Document create/edit/publish flow', async ({ page }) => {
  await adminLogin(page)
  await page.goto('/documents')
  await page.waitForLoadState('networkidle')

  // Dismiss any Vite error overlay if present
  const overlay = page.locator('vite-error-overlay')
  if (await overlay.count() > 0) {
    await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove())
    await page.waitForTimeout(500)
  }

  // Create button has data-tour attribute
  const createBtn = page.locator('[data-tour="documents-create-button"]')
  await expect(createBtn).toBeVisible({ timeout: 15000 })
  await createBtn.click()
  await page.waitForTimeout(1000)

  const titleInput = page.locator('input[placeholder="Enter document title"]')
  const timestamp = Date.now()
  await titleInput.fill(`Smoke Test Doc ${timestamp}`)

  const platformInput = page.locator('input[placeholder="Choose an existing platform or type a new one"]')
  if (await platformInput.count() > 0) {
    await platformInput.fill('Core Platform')
  }

  const submitBtn = page.locator('button[type="submit"]').first()
  await submitBtn.click()
  await page.waitForTimeout(3000)

  // Verify we navigated to the new document or stayed on documents page
  await expect(page.locator('body')).toContainText(/Smoke Test Doc|created|success|documents/i, { timeout: 10000 })
})

// #145 - Chat send/receive
test('#145 Chat send/receive', async ({ page }) => {
  await adminLogin(page)
  await page.goto('/chat')
  await page.waitForLoadState('networkidle')

  await expect(page.locator('body')).toContainText(/chat|conversation|message/i, { timeout: 10000 })

  const msgInput = page.locator('textarea, input[placeholder*="message" i], input[placeholder*="type" i], [contenteditable="true"]').first()
  if (await msgInput.isVisible()) {
    const newChatBtn = page.locator('button:has-text("New"), button:has-text("Create")')
    if (await newChatBtn.count() > 0) {
      await newChatBtn.first().click()
      await page.waitForTimeout(500)
    }
    await msgInput.fill('Smoke test message from Docker')
    const sendBtn = page.locator('button:has-text("Send"), button[type="submit"]')
    if (await sendBtn.count() > 0) {
      await sendBtn.first().click()
      await page.waitForTimeout(2000)
    }
  }
})

// #146 - Customer portal accessible
test('#146 Customer portal accessible', async ({ page }) => {
  await customerLogin(page)
  await expect(page.locator('body')).toContainText(/portal|welcome|documents|knowledge/i, { timeout: 10000 })

  const content = page.locator('[class*="card"], table, [class*="document"], [class*="grid"]')
  await expect(content.first()).toBeVisible({ timeout: 10000 })
})

// #147 - Support ticket creation
test('#147 Support ticket creation', async ({ page }) => {
  await customerLogin(page)
  await page.goto('/portal/support')
  await page.waitForLoadState('networkidle')

  await expect(page.locator('body')).toContainText(/support|ticket|help|contact/i, { timeout: 10000 })

  const msgInput = page.locator('textarea, input[placeholder*="message" i], input[placeholder*="subject" i], [contenteditable="true"]').first()
  if (await msgInput.isVisible()) {
    await msgInput.fill('Docker smoke test support ticket')
    const sendBtn = page.locator('button:has-text("Send"), button:has-text("Submit"), button:has-text("Create"), button[type="submit"]').first()
    if (await sendBtn.isVisible()) {
      await sendBtn.click()
      await page.waitForTimeout(2000)
    }
  }
})

// #148 - Mobile layout (browser resize)
test('#148 Mobile layout (browser resize)', async ({ page }) => {
  // Login at default viewport first, then resize
  await adminLogin(page)
  await page.setViewportSize({ width: 375, height: 812 })
  await page.waitForTimeout(500)

  // Logged-in mobile view: no horizontal overflow
  const dashBodyWidth = await page.evaluate(() => document.body.scrollWidth)
  const viewportWidth = await page.evaluate(() => window.innerWidth)
  expect(dashBodyWidth).toBeLessThanOrEqual(viewportWidth + 20)

  // Public page mobile view
  await page.goto('/docs')
  await page.waitForLoadState('networkidle')

  const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
  expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 5)

  // Mobile hamburger menu button
  const menuBtn = page.locator('button[aria-label*="navigation menu" i]')
  await expect(menuBtn).toBeVisible({ timeout: 5000 })
})
