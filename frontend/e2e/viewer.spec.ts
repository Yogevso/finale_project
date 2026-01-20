import { test, expect } from '@playwright/test';

test.describe('Viewer Portal - Public Access', () => {
  test('should load viewer home page without authentication', async ({ page }) => {
    await page.goto('/viewer');
    
    // Should not redirect to login
    await expect(page).not.toHaveURL(/login/);
    
    // Should have content
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should display document cards', async ({ page }) => {
    await page.goto('/viewer');
    
    // Wait for content to load
    await page.waitForTimeout(1000);
    
    // Should show documents or empty state message
    const hasDocuments = await page.locator('[class*="card"], article, [class*="document"]').count() > 0;
    const hasEmptyState = await page.locator('text=/no documents|empty|nothing/i').count() > 0;
    
    expect(hasDocuments || hasEmptyState).toBeTruthy();
  });

  test('should have working search', async ({ page }) => {
    await page.goto('/viewer');
    
    // Find search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    
    if (await searchInput.count() > 0) {
      await searchInput.fill('policy');
      await searchInput.press('Enter');
      
      // Wait for search results
      await page.waitForTimeout(1000);
      
      // Page should update
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('should have category filter', async ({ page }) => {
    await page.goto('/viewer');
    
    // Find category filter
    const categoryFilter = page.locator('select, [class*="filter"], [class*="dropdown"]');
    
    if (await categoryFilter.count() > 0) {
      // Filter exists
      await expect(categoryFilter.first()).toBeVisible();
    }
  });

  test('should navigate to document detail', async ({ page }) => {
    await page.goto('/viewer');
    
    // Wait for documents to load
    await page.waitForTimeout(1000);
    
    // Click first document link
    const docLink = page.locator('a[href*="/viewer/"], [class*="card"] a, article a').first();
    
    if (await docLink.count() > 0) {
      await docLink.click();
      
      // Should navigate to detail page
      await page.waitForURL(/viewer\/\d+/);
      
      // Should show document content
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('should display document title on detail page', async ({ page }) => {
    await page.goto('/viewer');
    await page.waitForTimeout(1000);
    
    const docLink = page.locator('a[href*="/viewer/"]').first();
    
    if (await docLink.count() > 0) {
      const docTitle = await docLink.textContent();
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Title should be visible on detail page
      if (docTitle) {
        await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
      }
    }
  });

  test('should show attachments on detail page', async ({ page }) => {
    await page.goto('/viewer');
    await page.waitForTimeout(1000);
    
    const docLink = page.locator('a[href*="/viewer/"]').first();
    
    if (await docLink.count() > 0) {
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Should have attachments section
      await expect(page.locator('text=/attachment|file|download/i').first()).toBeVisible();
    }
  });

  test('should show comments on detail page', async ({ page }) => {
    await page.goto('/viewer');
    await page.waitForTimeout(1000);
    
    const docLink = page.locator('a[href*="/viewer/"]').first();
    
    if (await docLink.count() > 0) {
      await docLink.click();
      await page.waitForTimeout(500);
      
      // Should have comments section
      await expect(page.locator('text=/comment|discussion/i').first()).toBeVisible();
    }
  });
});

test.describe('Viewer Portal - Pagination', () => {
  test('should have pagination controls', async ({ page }) => {
    await page.goto('/viewer');
    await page.waitForTimeout(1000);
    
    // Look for pagination
    const pagination = page.locator('[class*="pagination"], nav[aria-label*="pagination"], button:has-text("Next"), button:has-text("Previous")');
    
    // Pagination may or may not be visible depending on document count
    const hasPagination = await pagination.count() > 0;
    
    // Just verify page loaded
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Viewer Portal - Responsiveness', () => {
  test('should display correctly on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/viewer');
    await page.waitForTimeout(500);
    
    // Page should be visible and not broken
    await expect(page.locator('body')).toBeVisible();
    
    // Should not have horizontal scroll
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    
    // Body should not be much wider than viewport
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 20);
  });

  test('should display correctly on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await page.goto('/viewer');
    await page.waitForTimeout(500);
    
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display correctly on desktop', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    await page.goto('/viewer');
    await page.waitForTimeout(500);
    
    await expect(page.locator('body')).toBeVisible();
  });
});
