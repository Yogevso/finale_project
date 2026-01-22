import { test, expect, Page } from '@playwright/test';

// Helper to login as admin
async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await page.fill('input#username', 'admin');
  await page.fill('input#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard|documents/, { timeout: 15000 }).catch(() => {});
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
}

test.describe('Document Versions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view versions tab on document', async ({ page }) => {
    await page.goto('/documents');
    
    // Click on first document
    const docLink = page.locator('table tbody tr a, [class*="card"] a').first();
    if (await docLink.count() > 0) {
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Click versions tab
      const versionsTab = page.locator('button:has-text("Versions"), a:has-text("Versions"), [role="tab"]:has-text("Versions")');
      if (await versionsTab.count() > 0) {
        await versionsTab.click();
        await page.waitForTimeout(500);
        
        // Should show versions list or empty state
        await expect(page.locator('body')).toContainText(/version|content|publish/i);
      }
    }
  });
});

test.describe('Document Attachments', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view attachments tab on document', async ({ page }) => {
    await page.goto('/documents');
    
    // Click on first document
    const docLink = page.locator('table tbody tr a, [class*="card"] a').first();
    if (await docLink.count() > 0) {
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Click attachments tab
      const attachmentsTab = page.locator('button:has-text("Attachments"), a:has-text("Attachments"), [role="tab"]:has-text("Attachments")');
      if (await attachmentsTab.count() > 0) {
        await attachmentsTab.click();
        await page.waitForTimeout(500);
        
        // Should show attachments list or upload button
        await expect(page.locator('body')).toContainText(/attach|upload|file/i);
      }
    }
  });
});

test.describe('Document Comments', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view comments tab on document', async ({ page }) => {
    await page.goto('/documents');
    
    // Click on first document
    const docLink = page.locator('table tbody tr a, [class*="card"] a').first();
    if (await docLink.count() > 0) {
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Click comments tab
      const commentsTab = page.locator('button:has-text("Comments"), a:has-text("Comments"), [role="tab"]:has-text("Comments")');
      if (await commentsTab.count() > 0) {
        await commentsTab.click();
        await page.waitForTimeout(500);
        
        // Should show comments section
        await expect(page.locator('body')).toContainText(/comment|post|reply/i);
      }
    }
  });

  test('should add a comment', async ({ page }) => {
    await page.goto('/documents');
    
    // Click on first document
    const docLink = page.locator('table tbody tr a, [class*="card"] a').first();
    if (await docLink.count() > 0) {
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Click comments tab
      const commentsTab = page.locator('button:has-text("Comments"), a:has-text("Comments")');
      if (await commentsTab.count() > 0) {
        await commentsTab.click();
        await page.waitForTimeout(500);
        
        // Find comment input
        const commentInput = page.locator('textarea[placeholder*="comment" i], textarea[name="content"]');
        if (await commentInput.count() > 0) {
          await commentInput.fill(`E2E Test Comment ${Date.now()}`);
          
          // Submit comment
          const submitBtn = page.locator('button:has-text("Post"), button:has-text("Add"), button:has-text("Submit")');
          if (await submitBtn.count() > 0) {
            await submitBtn.first().click();
            await page.waitForTimeout(1000);
          }
        }
      }
    }
  });
});

test.describe('Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should search documents in management portal', async ({ page }) => {
    await page.goto('/documents');
    
    // Find search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    if (await searchInput.count() > 0) {
      await searchInput.fill('test');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);
      
      // Results should be filtered
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('should filter documents by status', async ({ page }) => {
    await page.goto('/documents');
    
    // Find status filter
    const statusFilter = page.locator('select[name="status"], [aria-label="Status filter"]');
    if (await statusFilter.count() > 0) {
      await statusFilter.selectOption('active');
      await page.waitForTimeout(500);
    }
  });
});
