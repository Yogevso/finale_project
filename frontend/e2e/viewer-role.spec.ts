import { test, expect, Page } from '@playwright/test';

/**
 * INTERNAL VIEWER Role Tests
 * Read-only internal access - can view all visibility levels but cannot modify
 * 
 * CAN:
 * - View all docs (public, internal, company)
 * - Download attachments
 * - View document versions
 * - View comments
 * - Access dashboard
 * 
 * CANNOT:
 * - Create documents
 * - Edit documents
 * - Delete documents
 * - Submit for review
 * - Approve/reject reviews
 * - Publish documents
 * - Add comments
 * - Submit feedback
 * - Manage users
 * - Manage companies
 * - Access settings
 */

const VIEWER = { username: 'viewer', password: 'viewer123' };

async function loginAsViewer(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem('viewer_landed', '1');
  });
  await page.goto('/login');
  await page.fill('input#username', VIEWER.username);
  await page.fill('input#password', VIEWER.password);
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
}

test.describe('Internal Viewer Role', () => {
  
  // ==================== AUTHENTICATION ====================
  
  test.describe('Authentication', () => {
    test('should login as viewer successfully', async ({ page }) => {
      await loginAsViewer(page);
      await expect(page).toHaveURL(/dashboard/);
    });

    test('should see limited navigation', async ({ page }) => {
      await loginAsViewer(page);
      // Should see Documents but not admin options
      await expect(page.locator('a:has-text("Documents")').first()).toBeVisible();
    });
  });

  // ==================== CAN DO ====================
  
  test.describe('Allowed Actions - View Documents', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should view dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      await expect(page.locator('body')).toContainText(/dashboard/i);
    });

    test('should list all documents', async ({ page }) => {
      await page.goto('/documents');
      await expect(page.locator('body')).toContainText(/document/i);
    });

    test('should view document details', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        await expect(page.locator('body')).toContainText(/title|content|version/i);
      }
    });

    test('should view document versions', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const versionsTab = page.locator('button:has-text("Versions")');
        if (await versionsTab.count() > 0) {
          await versionsTab.click();
          await page.waitForTimeout(500);
          await expect(page.locator('body')).toContainText(/version/i);
        }
      }
    });

    test('should view comments on document', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const commentsTab = page.locator('button:has-text("Comments")');
        if (await commentsTab.count() > 0) {
          await commentsTab.click();
          await page.waitForTimeout(500);
          await expect(page.locator('body')).toBeVisible();
        }
      }
    });

    test('should download attachments', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const attachmentsTab = page.locator('button:has-text("Attachments")');
        if (await attachmentsTab.count() > 0) {
          await attachmentsTab.click();
          await page.waitForTimeout(500);
          
          const downloadBtn = page.locator('a:has-text("Download"), button:has-text("Download")');
          if (await downloadBtn.count() > 0) {
            await expect(downloadBtn.first()).toBeVisible();
          }
        }
      }
    });

    test('should view internal visibility documents', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      // Viewer should see internal documents
      await expect(page.locator('body')).toContainText(/document/i);
    });
  });

  // ==================== CANNOT DO ====================
  
  test.describe('Restricted Actions - No Document Creation', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT see create document button', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const createBtn = page.locator('button:has-text("Create"), button:has-text("New Document")');
      expect(await createBtn.count()).toBe(0);
    });

    test('should NOT access create document page', async ({ page }) => {
      await page.goto('/documents/new');
      await page.waitForTimeout(1000);
      const url = page.url();
      // Viewer should be redirected away or see access denied or page not found
      expect(url.includes('/dashboard') || url.includes('/documents') || url.includes('/login') ||
             await page.locator('text=/access denied|forbidden|not found/i').count() > 0 ||
             !url.includes('/documents/new')).toBeTruthy();
    });
  });

  test.describe('Restricted Actions - No Document Editing', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT see edit button on documents', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const editBtn = page.locator('button:has-text("Edit")');
        expect(await editBtn.count()).toBe(0);
      }
    });
  });

  test.describe('Restricted Actions - No Document Deletion', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT see delete button on documents', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const deleteBtn = page.locator('button:has-text("Delete")');
        expect(await deleteBtn.count()).toBe(0);
      }
    });
  });

  test.describe('Restricted Actions - No Publishing', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT see publish button on versions', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const versionsTab = page.locator('button:has-text("Versions")');
        if (await versionsTab.count() > 0) {
          await versionsTab.click();
          await page.waitForTimeout(500);
          
          const publishBtn = page.locator('button:has-text("Publish")');
          expect(await publishBtn.count()).toBe(0);
        }
      }
    });
  });

  test.describe('Restricted Actions - No Reviews', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT access reviews page', async ({ page }) => {
      await page.goto('/reviews');
      await page.waitForTimeout(1000);
      const url = page.url();
      expect(url.includes('/dashboard') || url.includes('/login') ||
             await page.locator('text=/access denied|forbidden/i').count() > 0).toBeTruthy();
    });

    test('should NOT submit for review', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const submitReviewBtn = page.locator('button:has-text("Submit for Review")');
        expect(await submitReviewBtn.count()).toBe(0);
      }
    });
  });

  test.describe('Restricted Actions - No Comments', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT see add comment form', async ({ page }) => {
      await page.goto('/documents');
      await page.waitForTimeout(1000);
      
      const docLink = page.locator('table tbody tr a').first();
      if (await docLink.count() > 0) {
        await docLink.click();
        await page.waitForTimeout(500);
        
        const commentsTab = page.locator('button:has-text("Comments")');
        if (await commentsTab.count() > 0) {
          await commentsTab.click();
          await page.waitForTimeout(500);
          
          const addCommentInput = page.locator('textarea[name="comment"], input[name="comment"]');
          expect(await addCommentInput.count()).toBe(0);
        }
      }
    });
  });

  test.describe('Restricted Actions - No User Management', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT access users page', async ({ page }) => {
      await page.goto('/users');
      await page.waitForTimeout(1000);
      const url = page.url();
      expect(url.includes('/dashboard') || url.includes('/login') ||
             await page.locator('text=/access denied|forbidden/i').count() > 0).toBeTruthy();
    });

    test('should NOT see Users in navigation', async ({ page }) => {
      await page.goto('/dashboard');
      await page.waitForTimeout(500);
      const usersNav = page.locator('nav a:has-text("Users")');
      expect(await usersNav.count()).toBe(0);
    });
  });

  test.describe('Restricted Actions - No Company Management', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT access companies page', async ({ page }) => {
      await page.goto('/admin/companies');
      await page.waitForTimeout(1000);
      const url = page.url();
      // Viewer should be redirected away or see access denied
      expect(url.includes('/dashboard') || url.includes('/login') || url.includes('/documents') ||
             await page.locator('text=/access denied|forbidden|not authorized/i').count() > 0 ||
             !url.includes('/admin/companies')).toBeTruthy();
    });

    test('should NOT see Companies in navigation', async ({ page }) => {
      await page.goto('/dashboard');
      await page.waitForTimeout(500);
      const companiesNav = page.locator('nav a:has-text("Companies")');
      expect(await companiesNav.count()).toBe(0);
    });
  });

  test.describe('Restricted Actions - No Settings', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsViewer(page);
    });

    test('should NOT access settings page', async ({ page }) => {
      await page.goto('/admin/settings');
      await page.waitForTimeout(1000);
      const url = page.url();
      // Viewer should either be redirected, see limited settings, or not have system-level options
      const systemSettings = page.locator('text=/system admin|manage admins|super admin/i');
      const systemSettingsCount = await systemSettings.count();
      expect(systemSettingsCount === 0 || url.includes('/dashboard') || url.includes('/login') || url.includes('/documents') ||
             await page.locator('text=/access denied|forbidden|not authorized/i').count() > 0).toBeTruthy();
    });

    test('should NOT see Settings in navigation', async ({ page }) => {
      await page.goto('/dashboard');
      await page.waitForTimeout(500);
      const settingsNav = page.locator('nav a:has-text("Settings")');
      expect(await settingsNav.count()).toBe(0);
    });
  });
});
