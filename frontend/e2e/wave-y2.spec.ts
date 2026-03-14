/**
 * Wave Y.2 E2E tests — Y2-024, Y2-025, Y2-026
 */
import { test, expect, type Page } from '@playwright/test'
import { loginByApi } from './helpers/auth'
import { createDocumentViaApi } from './helpers/documents'

const ADMIN = { username: 'admin', password: 'admin123' }
const CUSTOMER = { username: 'customer1', password: 'customer123' }

async function loginAsAdmin(page: Page) {
  await loginByApi(page, ADMIN, /\/(dashboard|documents)/, '/dashboard')
}

async function loginAsCustomer(page: Page) {
  await loginByApi(page, CUSTOMER, /\/portal/, '/portal')
}

// ---------------------------------------------------------------------------
// Y2-024: Global search — type in header search bar, verify dropdown, click, navigate
// ---------------------------------------------------------------------------
test.describe('Y2-024: Global search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('typing in search bar shows dropdown with results', async ({ page }) => {
    const searchInput = page.getByRole('combobox', { name: /search documents/i })
    await expect(searchInput).toBeVisible()

    await searchInput.fill('test')

    // Wait for dropdown to appear (300ms debounce + API)
    const listbox = page.getByRole('listbox')
    await expect(listbox).toBeVisible({ timeout: 5000 })
  })

  test('clicking a search result navigates to document', async ({ page }) => {
    // Ensure at least one document exists
    await createDocumentViaApi(page, ADMIN, {
      title: 'SearchNav Target Doc',
      status: 'draft',
    })

    const searchInput = page.getByRole('combobox', { name: /search documents/i })
    await searchInput.fill('SearchNav Target')

    const listbox = page.getByRole('listbox')
    await expect(listbox).toBeVisible({ timeout: 5000 })

    // Click first result option
    const firstResult = page.getByRole('option').first()
    await firstResult.click()

    // Should navigate away from current page
    await expect(page).not.toHaveURL(/\/dashboard$/, { timeout: 5000 })
  })

  test('keyboard navigation in search dropdown', async ({ page }) => {
    const searchInput = page.getByRole('combobox', { name: /search documents/i })
    await searchInput.fill('test')

    const listbox = page.getByRole('listbox')
    await expect(listbox).toBeVisible({ timeout: 5000 })

    // Press ArrowDown to select first item
    await searchInput.press('ArrowDown')
    const firstOption = page.getByRole('option').first()
    await expect(firstOption).toHaveAttribute('aria-selected', 'true')

    // Escape closes dropdown
    await searchInput.press('Escape')
    await expect(listbox).not.toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// Y2-025: Customer portal personalized dashboard
// ---------------------------------------------------------------------------
test.describe('Y2-025: Personalized dashboard', () => {
  test('dashboard shows Recently Viewed and Continue Reading sections', async ({ page }) => {
    await loginAsCustomer(page)

    // The dashboard should be visible
    await expect(page.locator('body')).toContainText(/dashboard|welcome|portal/i, { timeout: 10000 })

    // Look for personalization sections (they may show empty states)
    const body = page.locator('body')
    const hasRecentlyViewed = await body.getByText(/recently viewed/i).count()
    const hasContinueReading = await body.getByText(/continue reading/i).count()

    // At least one personalization section should be present
    expect(hasRecentlyViewed + hasContinueReading).toBeGreaterThanOrEqual(1)
  })
})

// ---------------------------------------------------------------------------
// Y2-026: Advanced search builder
// ---------------------------------------------------------------------------
test.describe('Y2-026: Advanced search builder', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('open builder, set filters, search', async ({ page }) => {
    // Click the advanced search button
    const advancedBtn = page.getByRole('button', { name: /advanced search/i })
    await advancedBtn.click()

    // Modal should appear with filter fields
    await expect(page.getByText(/advanced search/i)).toBeVisible({ timeout: 3000 })

    // Fill in a query
    const queryInput = page.locator('input[type="text"]').first()
    await queryInput.fill('deployment')

    // Click Search button inside modal
    const searchBtn = page.getByRole('button', { name: /^search$/i })
    await searchBtn.click()

    // Should navigate to documents page with search params
    await expect(page).toHaveURL(/\/documents\?/, { timeout: 5000 })
  })

  test('reset clears all filters', async ({ page }) => {
    const advancedBtn = page.getByRole('button', { name: /advanced search/i })
    await advancedBtn.click()

    await expect(page.getByText(/advanced search/i)).toBeVisible({ timeout: 3000 })

    // Fill a query
    const queryInput = page.locator('input[type="text"]').first()
    await queryInput.fill('something')

    // Click Reset
    const resetBtn = page.getByRole('button', { name: /reset/i })
    await resetBtn.click()

    // Input should be cleared
    await expect(queryInput).toHaveValue('')
  })
})
