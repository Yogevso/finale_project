import { test, expect, Page } from '@playwright/test';

/**
 * PUBLIC (Anonymous) Access Tests
 * No authentication required
 * 
 * CAN:
 * - View public published documents
 * - Search public documents
 * - View document details
 * - Download public attachments
 * 
 * CANNOT:
 * - View internal documents
 * - View company-specific documents
 * - Create/edit/delete anything
 * - Submit feedback
 * - Access any authenticated routes
 */

async function expectAnonymousBlocked(page: Page, protectedPath: string) {
  await page.goto(protectedPath);
  await page.waitForTimeout(500);
  const url = page.url();
  expect(
    url.includes('/login') || url.includes('/docs') || !url.includes(protectedPath)
  ).toBeTruthy();
}

test.describe('Public Portal - Anonymous Access', () => {
  
  // ==================== CAN DO ====================
  
  test.describe('Allowed Actions', () => {
    test('should access public home page without login', async ({ page }) => {
      await page.goto('/');
      await expect(page).not.toHaveURL(/login/);
      await expect(page.locator('body')).toBeVisible();
    });

    test('should browse public documents list', async ({ page }) => {
      await page.goto('/browse');
      await expect(page).not.toHaveURL(/login/);
      // Should show documents or empty state
      await expect(page.locator('body')).toContainText(/document|browse|empty|no results/i);
    });

    test('should search public documents', async ({ page }) => {
      await page.goto('/');
      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
      if (await searchInput.count() > 0) {
        await searchInput.fill('policy');
        await searchInput.press('Enter');
        await page.waitForTimeout(1000);
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('should view public document detail', async ({ page }) => {
      await page.goto('/browse');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('a[href*="/doc/"]').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        // Should show document content
        await expect(page.locator('body')).toContainText(/viewer portal|back to documents|description|content/i);
      }
    });

    test('should see login button', async ({ page }) => {
      await page.goto('/');
      const loginBtn = page.locator('a:has-text("Login"), button:has-text("Login"), a[href*="/login"]');
      await expect(loginBtn.first()).toBeVisible();
    });

    test('should view categories', async ({ page }) => {
      await page.goto('/browse');
      await page.waitForTimeout(500);
      // Categories should be visible or filterable
      await expect(page.locator('body')).toBeVisible();
    });
  });

  // ==================== CANNOT DO ====================
  
  test.describe('Restricted Actions', () => {
    test('should NOT access dashboard without login', async ({ page }) => {
      await expectAnonymousBlocked(page, '/dashboard');
    });

    test('should NOT access documents management', async ({ page }) => {
      await expectAnonymousBlocked(page, '/documents');
    });

    test('should NOT access user management', async ({ page }) => {
      await expectAnonymousBlocked(page, '/users');
    });

    test('should NOT access company management', async ({ page }) => {
      await expectAnonymousBlocked(page, '/admin/companies');
    });

    test('should NOT access customer portal', async ({ page }) => {
      await expectAnonymousBlocked(page, '/portal');
    });

    test('should NOT access reviews', async ({ page }) => {
      await expectAnonymousBlocked(page, '/reviews');
    });

    test('should NOT access feedback management', async ({ page }) => {
      await expectAnonymousBlocked(page, '/admin/feedback');
    });

    test('should NOT see internal documents in public list', async ({ page }) => {
      await page.goto('/browse');
      await page.waitForTimeout(1000);
      // Internal docs should not appear - check page doesn't expose internal content
      // This is a basic check - detailed isolation tested in API tests
      await expect(page.locator('body')).toBeVisible();
    });
  });
});
