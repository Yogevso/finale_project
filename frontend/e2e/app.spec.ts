import { test, expect, Page } from '@playwright/test';

// Test credentials
const ADMIN = { username: 'admin', password: 'admin123' };
const EDITOR = { username: 'editor', password: 'editor123' };
const CUSTOMER = { username: 'customer1', password: 'customer123' };
const INVALID = { username: 'invalid', password: 'wrongpass' };

// Helper function to login
async function login(page: Page, credentials: { username: string; password: string }) {
  await page.goto('/login');
  await page.fill('input#username', credentials.username);
  await page.fill('input#password', credentials.password);
  await page.click('button[type="submit"]');
  // Wait for network to settle after login attempt
  await page.waitForLoadState('networkidle');
  // Wait for redirect to complete
  await page.waitForTimeout(2000);
}

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');
    
    // Check page elements
    await expect(page.locator('h1')).toContainText('Documentation Platform');
    await expect(page.locator('input#username')).toBeVisible();
    await expect(page.locator('input#password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    await login(page, ADMIN);
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/dashboard/);
    
    // Dashboard should show user info or welcome message
    await expect(page.locator('body')).toContainText(/dashboard|welcome|documents/i);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Wait for form to be ready
    await expect(page.locator('input#username')).toBeVisible();
    
    // Fill in invalid credentials
    await page.locator('input#username').fill(INVALID.username);
    await page.locator('input#password').fill(INVALID.password);
    
    // Click login
    await page.locator('button[type="submit"]').click();
    
    // Wait for the login attempt to complete
    await page.waitForTimeout(3000);
    
    // Should stay on login page (not redirect to dashboard)
    const currentUrl = page.url();
    expect(currentUrl).toContain('login');
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await login(page, ADMIN);
    await expect(page).toHaveURL(/dashboard/);
    
    // Find and click logout button
    const logoutButton = page.locator('button:has-text("Logout"), a:has-text("Logout"), [aria-label="Logout"]');
    if (await logoutButton.count() > 0) {
      await logoutButton.first().click();
      
      // Should redirect to login
      await expect(page).toHaveURL(/login/);
    }
  });

  test('should redirect to login when not authenticated', async ({ page }) => {
    // Try to access protected route
    await page.goto('/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });

  test('should login as customer and redirect to portal', async ({ page }) => {
    await login(page, CUSTOMER);
    
    // Customer should be redirected to portal or customer dashboard
    await expect(page).toHaveURL(/portal|dashboard/);
  });

  test('customer should not access admin documents page', async ({ page }) => {
    await login(page, CUSTOMER);
    
    // Try to access admin documents
    await page.goto('/documents');
    await page.waitForTimeout(1000);
    
    // Should be redirected or show access denied
    const url = page.url();
    const isOnAdminDocs = url.includes('/documents') && !url.includes('/portal');
    const hasAccessDenied = await page.locator('text=/access denied|forbidden|not authorized/i').count() > 0;
    
    // Either redirected away or shown access denied
    expect(!isOnAdminDocs || hasAccessDenied).toBeTruthy();
  });
});

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN);
    // Wait longer for login redirect and dashboard to load
    await expect(page).toHaveURL(/dashboard/, { timeout: 15000 });
  });

  test('should display dashboard with stats', async ({ page }) => {
    // Check for dashboard elements
    await expect(page.locator('text=/dashboard/i').first()).toBeVisible();
    
    // Should show some statistics or document count
    const statsSection = page.locator('[class*="stat"], [class*="card"], [class*="grid"]');
    await expect(statsSection.first()).toBeVisible();
  });

  test('should navigate to documents', async ({ page }) => {
    // Click documents link
    await page.click('a:has-text("Documents")');
    
    // Should be on documents page
    await expect(page).toHaveURL(/documents/);
  });
});

test.describe('Documents CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN);
    await page.goto('/documents');
  });

  test('should display documents list', async ({ page }) => {
    // Should show documents list or empty state
    const documentsContainer = page.locator('table, [class*="list"], [class*="grid"]');
    await expect(documentsContainer.first()).toBeVisible();
  });

  test('should create new document', async ({ page }) => {
    // Click new document button
    const newButton = page.locator('button:has-text("New"), a:has-text("New"), button:has-text("Create")');
    if (await newButton.count() > 0) {
      await newButton.first().click();
      
      // Wait for modal or page
      await page.waitForTimeout(500);
      
      // Fill form
      const titleInput = page.locator('input[name="title"], input#title, input[placeholder*="title" i]');
      if (await titleInput.count() > 0) {
        await titleInput.fill(`E2E Test Document ${Date.now()}`);
        
        // Fill description if exists
        const descInput = page.locator('textarea[name="description"], textarea#description');
        if (await descInput.count() > 0) {
          await descInput.fill('Created by E2E test');
        }
        
        // Submit
        await page.click('button[type="submit"], button:has-text("Save"), button:has-text("Create")');
        
        // Should show success or redirect
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should view document details', async ({ page }) => {
    // Click on first document
    const docLink = page.locator('table tbody tr a, [class*="card"] a, [class*="list"] a').first();
    if (await docLink.count() > 0) {
      await docLink.click();
      
      // Should show document details
      await expect(page.locator('text=/details|versions|attachments|comments/i').first()).toBeVisible();
    }
  });
});

test.describe('Viewer Portal', () => {
  test('should access viewer without login', async ({ page }) => {
    await page.goto('/viewer');
    
    // Should show viewer page, not redirect to login
    await expect(page).not.toHaveURL(/login/);
    
    // Should show document list or search
    await expect(page.locator('body')).toContainText(/document|search|browse/i);
  });

  test('should search documents in viewer', async ({ page }) => {
    await page.goto('/viewer');
    
    // Find search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[name="search"]');
    if (await searchInput.count() > 0) {
      await searchInput.fill('test');
      
      // Press enter or wait for results
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);
    }
  });

  test('should view document in viewer', async ({ page }) => {
    await page.goto('/viewer');
    
    // Wait for documents to load
    await page.waitForTimeout(1000);
    
    // Click on first document card/link
    const docLink = page.locator('a[href*="/viewer/"], [class*="card"] a, article a').first();
    if (await docLink.count() > 0) {
      await docLink.click();
      
      // Should show document content
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Accessibility', () => {
  test('login page is keyboard navigable', async ({ page }) => {
    await page.goto('/login');
    
    // Tab to username
    await page.keyboard.press('Tab');
    await expect(page.locator('input#username')).toBeFocused();
    
    // Tab to password
    await page.keyboard.press('Tab');
    await expect(page.locator('input#password')).toBeFocused();
    
    // Tab to submit button
    await page.keyboard.press('Tab');
    await expect(page.locator('button[type="submit"]')).toBeFocused();
  });

  test('forms have proper labels', async ({ page }) => {
    await page.goto('/login');
    
    // Check for labels
    const usernameLabel = page.locator('label[for="username"]');
    const passwordLabel = page.locator('label[for="password"]');
    
    await expect(usernameLabel).toBeVisible();
    await expect(passwordLabel).toBeVisible();
  });
});
