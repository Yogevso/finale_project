import { test, expect, type Page } from '@playwright/test';

async function gotoLogin(page: Page) {
  // The app redirects first-time visitors from /login to /docs.
  await page.addInitScript(() => {
    window.sessionStorage.setItem('viewer_landed', '1');
  });
  await page.goto('/login');
}

async function loginAsAdmin(page: Page) {
  await gotoLogin(page);
  await page.fill('input#username', 'admin');
  await page.fill('input#password', 'admin123');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/(dashboard|documents)/, { timeout: 20000 });
}

async function openDocuments(page: Page) {
  await page.goto('/documents');
  await expect(page).toHaveURL(/\/documents/, { timeout: 15000 });
}

async function createDocument(page: Page, title: string) {
  await openDocuments(page);
  await page.getByRole('button', { name: /new document/i }).click();
  await expect(page.getByText('Create Document')).toBeVisible();
  await page.fill('input[placeholder="Enter document title"]', title);
  await page.fill('textarea[placeholder="Brief description"]', 'Created by Playwright E2E');
  await page.getByRole('button', { name: /create & continue editing/i }).click();
  await expect(page).toHaveURL(/\/documents\/\d+\/fullscreen/, { timeout: 30000 });
}

async function openExistingDocumentOrCreate(page: Page) {
  await openDocuments(page);
  const firstDocLink = page.locator('table tbody tr a[href*="/documents/"]').first();

  if ((await firstDocLink.count()) > 0) {
    await firstDocLink.click();
    await expect(page).toHaveURL(/\/documents\/\d+\/fullscreen/, { timeout: 15000 });
    return;
  }

  await createDocument(page, `E2E Docs Spec ${Date.now()}`);
}

test.describe('Document Versions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view versions tab on document', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    await page.getByRole('button', { name: /versions/i }).click();
    await expect(page.locator('body')).toContainText(/version|publish|no versions/i);
  });
});

test.describe('Document Attachments', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view attachments tab on document', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    await page.getByRole('button', { name: /attachments/i }).click();
    await expect(page.locator('body')).toContainText(/attachment|upload|file/i);
  });
});

test.describe('Document Comments', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view comments tab on document', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    await page.getByRole('button', { name: /comments/i }).click();
    await expect(page.locator('body')).toContainText(/comments?|post comment|no comments yet/i);
  });

  test('should add a comment', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    await page.getByRole('button', { name: /comments/i }).click();

    const comment = `E2E Test Comment ${Date.now()}`;
    const commentInput = page.locator('textarea[placeholder*="comment" i]').first();
    await expect(commentInput).toBeVisible();
    await commentInput.fill(comment);

    await page.getByRole('button', { name: /post comment/i }).click();
    await expect(page.locator('body')).toContainText(comment);
  });
});

test.describe('Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should search documents in management portal', async ({ page }) => {
    await openDocuments(page);

    const searchInput = page.locator('input[placeholder*="Search documents" i]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('test');
    await expect(searchInput).toHaveValue('test');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should filter documents by status', async ({ page }) => {
    await openDocuments(page);

    const statusSummary = page.locator('summary').filter({ hasText: /Status:/i });
    await expect(statusSummary).toBeVisible();
    await statusSummary.click();

    await page.getByRole('button', { name: 'Published' }).click();
    await expect(statusSummary).toContainText(/Status:\s*Published/i);
  });
});
