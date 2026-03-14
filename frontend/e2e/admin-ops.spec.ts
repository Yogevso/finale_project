import { test, expect, type Page } from '@playwright/test'
import { loginByApi, getApiAuthHeaders } from './helpers/auth'

/**
 * Wave Z – Admin Operations E2E Tests
 *
 * Z-022: admin tenant provisioning wizard
 * Z-023: admin impersonation mode
 * Z-024: custom branding
 */

const SYSTEM_ADMIN = { username: 'sysadmin', password: 'sysadmin123' }

async function loginAsSystemAdmin(page: Page) {
  await loginByApi(page, SYSTEM_ADMIN, /\/(dashboard|documents|admin)/, '/dashboard')
}

// ── Z-022: Admin Tenant Provisioning Wizard ──────────────────────

test.describe('Z-022 Admin Tenant Provisioning', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSystemAdmin(page)
  })

  test('should navigate to admin operations page', async ({ page }) => {
    await page.goto('/admin/operations')
    await expect(page.locator('h1')).toContainText('Admin Operations')
    await expect(page.locator('text=System Admin')).toBeVisible()
  })

  test('should provision a new tenant via the wizard', async ({ page }) => {
    await page.goto('/admin/operations')

    // Switch to Tenant Management tab
    await page.click('button:has-text("Tenant Management")')

    // Open provisioning form
    await page.click('button:has-text("Provision Tenant")')

    // Fill in the form
    const slug = `e2e-tenant-${Date.now()}`
    await page.fill('input[placeholder="Tenant Name"]', 'E2E Test Tenant')
    await page.fill('input[placeholder*="Slug"]', slug)
    await page.fill('input[placeholder="Admin Username"]', `e2etenant_admin_${Date.now()}`)
    await page.fill('input[placeholder="Admin Email"]', `e2e-${Date.now()}@example.com`)
    await page.fill('input[placeholder="Admin Password"]', 'TestPass123!')
    await page.fill('input[placeholder="Contact Email"]', 'contact@e2etest.com')

    // Submit
    await page.click('button:has-text("Create")')

    // Wait for success toast or the tenant to appear
    await expect(
      page.locator('text=E2E Test Tenant').first()
    ).toBeVisible({ timeout: 10000 })
  })
})

// ── Z-023: Admin Impersonation Mode ──────────────────────────────

test.describe('Z-023 Admin Impersonation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSystemAdmin(page)
  })

  test('should show impersonation panel', async ({ page }) => {
    await page.goto('/admin/operations')

    // Switch to Impersonation tab
    await page.click('button:has-text("Impersonation")')

    // Should see tenant selection
    await expect(page.locator('text=Select Tenant to Impersonate')).toBeVisible()
  })

  test('should start and end impersonation via API', async ({ page }) => {
    const headers = await getApiAuthHeaders(page, SYSTEM_ADMIN)

    // Get tenants to find one to impersonate
    const tenantsResp = await page.request.get('/api/v1/companies?per_page=5', { headers })
    expect(tenantsResp.ok()).toBeTruthy()
    const tenants = await tenantsResp.json()
    const items = tenants.items || []
    if (items.length === 0) {
      test.skip()
      return
    }

    const tenantId = items[0].id

    // Start impersonation
    const startResp = await page.request.post('/api/v1/admin/impersonate', {
      headers,
      data: { tenant_id: tenantId },
    })
    expect(startResp.ok()).toBeTruthy()
    const session = await startResp.json()
    expect(session.is_active).toBe(true)
    expect(session.target_tenant_id).toBe(tenantId)

    // Check current impersonation
    const currentResp = await page.request.get('/api/v1/admin/impersonate/current', { headers })
    expect(currentResp.ok()).toBeTruthy()
    const current = await currentResp.json()
    expect(current.id).toBe(session.id)

    // End impersonation
    const endResp = await page.request.post('/api/v1/admin/impersonate/end', { headers })
    expect(endResp.ok()).toBeTruthy()

    // Verify ended
    const afterResp = await page.request.get('/api/v1/admin/impersonate/current', { headers })
    expect(afterResp.ok()).toBeTruthy()
    const after = await afterResp.json()
    expect(after).toBeNull()
  })
})

// ── Z-024: Custom Branding ───────────────────────────────────────

test.describe('Z-024 Custom Branding', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSystemAdmin(page)
  })

  test('should update tenant branding via API', async ({ page }) => {
    const headers = await getApiAuthHeaders(page, SYSTEM_ADMIN)

    // Get a tenant
    const tenantsResp = await page.request.get('/api/v1/companies?per_page=5', { headers })
    expect(tenantsResp.ok()).toBeTruthy()
    const tenants = await tenantsResp.json()
    const items = tenants.items || []
    if (items.length === 0) {
      test.skip()
      return
    }

    const tenantId = items[0].id

    // Update branding
    const brandResp = await page.request.put(
      `/api/v1/admin/tenants/${tenantId}/branding`,
      {
        headers,
        data: {
          primary_color: '#3B82F6',
          accent_color: '#10B981',
          portal_header_text: 'E2E Branding Test',
        },
      },
    )
    expect(brandResp.ok()).toBeTruthy()
    const branding = await brandResp.json()
    expect(branding.primary_color).toBe('#3B82F6')
    expect(branding.accent_color).toBe('#10B981')
    expect(branding.portal_header_text).toBe('E2E Branding Test')

    // Verify read-back
    const readResp = await page.request.get(
      `/api/v1/admin/tenants/${tenantId}/branding`,
      { headers },
    )
    expect(readResp.ok()).toBeTruthy()
    const readBack = await readResp.json()
    expect(readBack.primary_color).toBe('#3B82F6')
  })
})
